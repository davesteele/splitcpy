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
    fullre = re.search('^(.+?)@(.+?):(.+)$', spec)
    smallre = re.search('^(.+?):(.+)$', spec)

    if fullre:
        return tuple([fullre.group(x) for x in range(1, 4)])
    elif smallre:
        user = getpass.getuser()
        return tuple([user] + [smallre.group(x) for x in range(1, 3)])
    else:
        return (None, None, spec)


def is_net_spec(spec):
    """Is the path spec of the form user@host:path?"""
    return parse_net_spec(spec)[0] is not None


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

    user, host, src_file = parse_net_spec(src_spec)
    p = fifo_path = None

    try:
        fifo_path = make_fifo()

        spltcmd = "splitcpy %s -s %d,%d,%d" % (src_file, num_slices,
                                               slice, bytes)
        sshcmd = "ssh -p %d %s@%s %s >%s" % (port, user, host, spltcmd,
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

    qs = []
    procs = []

    for n in range(num_slices):
        qs.append(Queue(10))
        procs.append(Process(target=dl_slice,
                     args=(src, num_slices, n, bytes, qs[n], pw, port)))
        procs[n].start()
        time.sleep(0.1)

    try:
        with open(dest, 'wb') as dfp:
            done = False
            while not done:
                for i in range(num_slices):
                    buf = qs[i].get()
                    if buf is None:
                        done = True
                    else:
                        dfp.write(buf)
    finally:
        [p.terminate() for p in procs if p.is_alive()]

    [p.join() for p in procs]


class CredException(Exception):
    pass


def establish_ssh_cred(user, host, port, pathlist):
    """Make a test ssh connection to determine the password, if needed"""

    quotedlist = ['"' + x + '"' for x in pathlist]
    remote_cmd = "splitcpy -f " + " ".join(quotedlist)
    cmd = "ssh -p %d %s@%s " % (port, user, host)
    cmd += remote_cmd
    password = None

    session = pexpect.spawn(cmd)
    while True:
        options = [
            'password: ', '}', pexpect.EOF, pexpect.TIMEOUT,
            'fingerprint',
        ]

        match = session.expect(options)

        if match == 0:
            password = getpass.getpass(session.before + 'password:')
            session.sendline(password)
        elif match == 1:
            # get the json in the ouput
            text = session.before + session.after
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
                usage="%(prog)s [user]@host:path [path]\n"
                      "       %(prog)s [user]@host:path [...] [dir]",
                description='Copy a remote file using multiple SSH streams.',
                epilog="The source file is remote. " +
                       "Remote files are specified as e.g. [user@]host:path. "
                       "'splitcpy' must be installed on both the local and "
                       "remote hosts.",
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
        help="filename, with optional path",
        )

    parser.add_argument(
        'dir',
        nargs='?',
        help="directory name (file name taken from source path)",
        )

    parser.add_argument(
        '-s',
        metavar='n,i,l',
        help="(internal use only) Generate file interleave of 'l'\
        bytes for the 'i'th slice out of 'n'",
        )

    parser.add_argument(
        '-f',
        action='store_true',
        help="(internal use only) Output far-side wildcard information",
        )

    parser.add_argument(
        '-p',
        metavar='port',
        dest='port',
        type=int,
        default=22,
        help='ssh port to use (if not the default)',
        )

    parser.add_argument(
        '-n',
        metavar='num',
        dest='num_slices',
        type=int,
        default=10,
        help='number of parallel slices to run (default=10)'
        )

    parser.add_argument(
        '-b',
        metavar='bytes',
        dest='slice_size',
        type=int,
        default=10000,
        help="chunk size for slices (default=10,000)"
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
            return "Invalid interleave argument"

    elif args.f:
        pass

    else:
        if len(args.fileargs) == 0:
            return "No files specified"

        if not is_net_spec(args.fileargs[0]):
            return "Currently only supports download copying"

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
            return "Malformed argument list"

        for src in args.rawsrcs:
            if parse_net_spec(args.rawsrcs[0])[0:2] != parse_net_spec(src)[0:2]:
                return "The user and host must be the same for all files"

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
            user, host = parse_net_spec(args.rawsrcs[0])[0:2]
            localized_srcs = [parse_net_spec(x)[2] for x in args.rawsrcs]
            password, remote_info = establish_ssh_cred(user, host, args.port,
                                                       localized_srcs)

            for src in remote_info['entries']:
                srcfile = src[3]
                path = parse_net_spec(srcfile)[2]

                dest = args.rawdest
                if os.path.isdir(dest):
                    dest = os.path.join(dest, os.path.basename(path))

                dl_file(args.rawsrcs[0], dest, args.num_slices,
                      args.slice_size, password, args.port)

        except CredException:
            print("Error establishing contact with remote splitcpy")
            sys.exit(-1)


if __name__ == '__main__':
    main(sys.argv[1:])
