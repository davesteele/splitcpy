#!/usr/bin/python
# Copyright 2015 David Steele <dsteele@gmail.com>
#
# This file is part of splitcpy.
#
# splitcpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# splitcpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with splitcpy.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import sys
import re
from multiprocessing import Process, Queue
import subprocess
import pexpect
import getpass
import os
import shutil
import uuid
import time
import tempfile
import glob
import json
import itertools

from collections import namedtuple
from distutils.version import LooseVersion

import locale
import gettext

locale.setlocale(locale.LC_ALL, '')
gettext.textdomain('splitcpy')
_ = gettext.gettext


"""
Copy file over split multiple SSH streams

Main entry points:

    establish_ssh_cred()
        Verify ssh connectivity and determine pw, if needed

    output_split()
        write out one of the stripes for a file, for transmisison

    dl_file()
        retrieve a file from a remote host using multiple ssh streams
"""


def parse_net_spec(spec):
    """Parse user@host:path into user, host, path"""

    PathSpec = namedtuple('PathSpec', "user, host, path")

    fullre = re.search('^(.+?)@(.+?):(.+)$', spec)
    smallre = re.search('^(.+?):(.+)$', spec)

    values = None
    if fullre:
        values = [fullre.group(x) for x in range(1, 4)]
    elif smallre:
        user = getpass.getuser()
        values = [user] + [smallre.group(x) for x in range(1, 3)]
    else:
        values = None, None, spec

    return PathSpec(*values)


def is_net_spec(spec):
    """Is the path spec of the form user@host:path?"""
    return parse_net_spec(spec).user is not None


def make_net_spec(user, host, path):
    return "{0}@{1}:{2}".format(user, host, path)

def slice_iter(fp, num_slices, slice_num, bytes):
    """Iterator returning packets of an interleaved slice of a file"""
    fp.seek(slice_num*bytes, 0)

    while True:
        buf = fp.read(bytes)

        if not buf:
            break

        yield buf

        fp.seek((num_slices-1)*bytes, 1)


def output_split(srcfile, num_slices, slice, bytes, dst):
    """Send an interleave slice of srcfile to dst"""
    with open(srcfile, 'rb') as src:
        for pkt in slice_iter(src, num_slices, slice, bytes):
            dst.write(pkt)


def make_fifo():
    fifo_path = os.path.join(tempfile.mkdtemp(), uuid.uuid4().__str__())
    os.mkfifo(fifo_path)
    return fifo_path


def del_fifo(path):
    dir = '/'.join(path.split('/')[0:-1])
    shutil.rmtree(dir)


def dl_slice(src_spec, num_slices, slice, bytes, queue, pw, port):
    """Call a remote interleave slice of a file to download"""

    ns = parse_net_spec(src_spec)
    p = fifo_path = None

    try:
        fifo_path = make_fifo()

        spltcmd = "splitcpy \\'%s\\' -s %d,%d,%d" % (ns.path, num_slices,
                                               slice, bytes)
        sshcmd = "ssh -p %d %s@%s %s >%s" % (port, ns.user, ns.host, spltcmd,
                                             fifo_path)

        if pw is not None:
            sshcmd = "SSHPASS=%s sshpass -e %s" % (pw, sshcmd)

        p = subprocess.Popen(sshcmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE
                             )

        fp = open(fifo_path, 'rb')

        while True:
            buf = fp.read(bytes)

            if not buf:
                break

            queue.put(buf)
    finally:
        if p and p.poll() is None:
            p.kill()

        if fifo_path:
            del_fifo(fifo_path)

    queue.put(None)


def dl_file(src, dest, num_slices, bytes, pw, port):
    """Perform a parallel download of a file"""

    slist = []
    Slice = namedtuple("Slice", "queue, proc")

    try:
        for n in range(num_slices):
            q = Queue(10)
            p = Process(target=dl_slice,
                        args=(src, num_slices, n, bytes, q, pw, port)
            )
            slist.append(Slice(q, p))
            p.start()
            time.sleep(0.025)

        with open(dest, 'wb') as dfp:
            buf_iter = (s.queue.get() for s in itertools.cycle(slist))
            for buf in itertools.takewhile(lambda x: x is not None, buf_iter):
                dfp.write(buf)
    finally:
        [s.proc.terminate() for s in slist if s.proc.is_alive()]

    [s.proc.join() for s in slist]


class CredException(Exception):
    pass


def quote_path(file):
    for char in '#;&"\',?$ *[]':
        file = re.sub("\\" + char, "\\" + char, file)
        if char in '?*':
            file = re.sub("\\" + char, "\\" + char, file)

    return file

def establish_ssh_cred(user, host, port, pathlist):
    """Make a test ssh connection to determine the password, if needed"""

    quotedlist = [quote_path(x) for x in pathlist]
    remote_cmd = "splitcpy -f " + " ".join(quotedlist)
    cmd = "ssh -p %d %s@%s " % (port, user, host)
    cmd += remote_cmd
    password = None

    session = pexpect.spawn(cmd)
    while True:
        options = [
            'password: ', '}', pexpect.EOF, pexpect.TIMEOUT,
            # 'password: ' matches the password prompt from sshd
            'fingerprint', _('password: '),
        ]

        match = session.expect(options)

        if match == 0 or match == 5:
            password = getpass.getpass(session.before.decode() + _('password: '))
            session.sendline(password)
        elif match == 1:
            # get the json in the ouput
            text = session.before.decode() + session.after.decode()
            m = re.search("^.*?(\{.+\}).*?$", text, re.DOTALL)
            remote_info = json.loads(m.group(1))

            session.close()

            return password, remote_info
        elif match == 2:
            raise CredException
        elif match == 3:
            raise CredException
        elif match == 4:
            raise CredException


def eval_files(flist):
    info = {
                'version': __version__,     # flake8: noqa
                'entries': [],
           }

    for spec in flist:
        for entry in glob.glob(spec):
            type = 'f'
            if os.path.isdir(entry):
                type = 'd'

            readable = os.access(entry, os.R_OK)
            writeable = os.access(entry, os.W_OK)

            info['entries'].append([type, readable, writeable, entry])

    return info


def parse_args(args):
    """Return an argparse args object"""
    parser = argparse.ArgumentParser(
                usage="%(prog)s -h\n"
                      "       %(prog)s [options] [user@]host:path [path]\n"
                      "       %(prog)s [options] [user@]host:path [...] [dir]",
                description=
                      _('Copy a remote file using multiple SSH streams.'),
                epilog=_("The source file is remote. "
                       "Remote files are specified as e.g. [user@]host:path. "
                       "'splitcpy' must be installed on both the local and "
                       "remote hosts."),
            )

    parser.add_argument(
        'fileargs',
        nargs='*',
        help=argparse.SUPPRESS,
        )

    # 'path' and 'dir' only add help text - no arguments are parsed
    parser.add_argument(
        'path',
        nargs='?',
        help=_("filename, with optional path"),
        )

    parser.add_argument(
        'dir',
        nargs='?',
        help=_("directory name (file name taken from source path)"),
        )

    parser.add_argument(
        '-s',
        metavar='n,i,l',
        help=_("(internal use only) Generate file interleave of 'l' "
               "bytes for the 'i'th slice out of 'n'"),
        )

    parser.add_argument(
        '-f',
        action='store_true',
        help=_("(internal use only) Output far-side wildcard information"),
        )

    parser.add_argument(
        '-p',
        metavar='port',
        dest='port',
        type=int,
        default=22,
        help=_('ssh port to use (if not the default)'),
        )

    parser.add_argument(
        '-n',
        metavar='num',
        dest='num_slices',
        type=int,
        default=10,
        help=_('number of parallel slices to run (default=10)'),
        )

    parser.add_argument(
        '-b',
        metavar='bytes',
        dest='slice_size',
        type=int,
        default=10000,
        help=_("chunk size for slices (default=10,000)"),
        )

    args = parser.parse_args(args)

    msg = validate_args(args)
    if msg:
        parser.error(msg)

    return(args)


def validate_args(args):

    if args.s:
        try:
            params = args.s.split(',')
            assert(len(params) == 3)

            setattr(args, 'num_slices', int(params[0]))
            setattr(args, 'slice', int(params[1]))
            setattr(args, 'bytes', int(params[2]))

            assert(args.bytes > 0)
            assert(args.slice >= 0)
            assert(args.num_slices > 0)
            assert(args.num_slices > args.slice)
        except (IndexError, ValueError, AssertionError):
            return _("Invalid interleave argument")

    elif args.f:
        pass

    else:
        if len(args.fileargs) == 0:
            return _("No files specified")

        if not is_net_spec(args.fileargs[0]):
            return _("Currently only supports download copying")

        proclist = list(args.fileargs)
        args.rawsrcs = []
        while proclist and \
                is_net_spec(proclist[0]) == is_net_spec(args.fileargs[0]):
            args.rawsrcs.append(proclist.pop(0))

        if len(proclist) == 0:
            args.rawdest = '.'
        elif len(proclist) == 1:
            args.rawdest = proclist[0]
        else:
            return _("Malformed argument list")

        first_ns = parse_net_spec(args.rawsrcs[0])
        for src in args.rawsrcs:
            src_ns = parse_net_spec(src)
            if first_ns.user != src_ns.user or first_ns.host != src_ns.host:
                return _("The user and host must be the same for all files")

    return None


def main(args=sys.argv[1:]):
    args = parse_args(args)

    if args.s:                      # download - remote side
        outfp = sys.stdout
        if sys.version_info >= (3, 0):
            outfp = sys.stdout.buffer

        output_split(args.fileargs[0], args.num_slices, args.slice, args.bytes,
                     outfp)

    elif args.f:                    # establish password, remote side
        info = eval_files(args.fileargs)

        print(json.dumps(info, indent=2, separators=(',',':')))

    else:                           # download - local side
        try:
            ns = parse_net_spec(args.rawsrcs[0])
            localized_srcs = [parse_net_spec(x).path for x in args.rawsrcs]
            password, remote_info = establish_ssh_cred(ns.user, ns.host,
                                                       args.port,
                                                       localized_srcs)

            remote_ver = remote_info['version']
            if LooseVersion(remote_ver) < LooseVersion(__VER_DL_MIN__):
                print(_("Remote splitcpy is too old"))
                sys.exit(1)

            if LooseVersion(remote_ver) > LooseVersion(__VER_DL_MAX__):
                print(_("Remote splitcpy is too new - upgrade local copy"))
                sys.exit(1)

            for src in remote_info['entries']:
                srcfile = src[3]
                path = parse_net_spec(srcfile).path

                dest = args.rawdest
                if os.path.isdir(dest):
                    dest = os.path.join(dest, os.path.basename(path))

                srcspec = make_net_spec(ns.user, ns.host, path)
                dl_file(srcspec, dest, args.num_slices,
                      args.slice_size, password, args.port)

        except CredException:
            print(_("Error establishing contact with remote splitcpy"))
            sys.exit(-1)


if __name__ == '__main__':
    main(sys.argv[1:])      # pragma: no cover
