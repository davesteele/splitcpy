#!/usr/bin/python

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

def parse_net_spec(spec):
    """Parse user@host:path into user, host, path"""
    m = re.search('^(.+?)@(.+?):(.+)$', spec)

    if m:
        return [m.group(x) for x in range(1,4)]
    else:
        return [None, None, spec]

def is_net_spec(spec):
    """Is the path spec of the form user@host:path?"""
    return parse_net_spec(spec)[0] is not None

def parse_args():
    """Return an argparse args object"""
    parser = argparse.ArgumentParser(
                description='Copy a remote file using multiple SSH streams.',
                epilog="The source file is remote. " + \
                       "Remote files are specified as e.g. user@host:path",
            )

    parser.add_argument('srcfile',
                help="Source file",
            )

    parser.add_argument('destfile',
                nargs='?',
                default='',
                help="Destination file",
            )

    parser.add_argument('-s',
                metavar='n,i,l',
                help="Generate file interleave of 'l' bytes for the 'i'th\
                      slice out of 'n'(internal use only)",
            )

    parser.add_argument('-p',
                metavar='port',
                dest='port',
                type=int,
                default=22,
                help='ssh port to use (if not the default)',
            )

    parser.add_argument('-n',
                metavar='num',
                dest='num_slices',
                type=int,
                default=10,
                help='number of parallel slices to run (default=10)'
            )

    parser.add_argument('-b',
                metavar='bytes',
                dest='slice_size',
                type=int,
                default=10000,
                help="chunk size for slices (default=10,000)"
            )

    parser.add_argument('--version',
                action='version',
                version="%(prog)s " + __version__,
                help="return version and exit"
            )

    args = parser.parse_args()

    try:
        params = args.s.split(',')
        assert(len(params) == 3)

        setattr(args, 'num_slices', int(params[0]))
        setattr(args, 'slice', int(params[1]))
        setattr(args, 'bytes', int(params[2]))

        assert(args.bytes>0)
        assert(args.slice>=0)
        assert(args.num_slices>0)
        assert(args.num_slices>args.slice)
    except AttributeError:
        pass
    except (IndexError, ValueError, AssertionError):
        parser.error("Invalid interleave argument")

    if not args.s and (not is_net_spec(args.srcfile)
                       or is_net_spec(args.destfile)):
        parser.error("Currently only supports download copying")

    if not args.s and not args.destfile:
        args.destfile = parse_net_spec(args.srcfile)[2].split('/')[-1]

    return(args)


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

        spltcmd = "splitcpy %s -s %d,%d,%d" % (src_file, num_slices, slice, bytes)
        sshcmd = "ssh -p %d %s@%s %s >%s" % (port, user, host, spltcmd, fifo_path)

        if pw is not None:
            sshcmd = "SSHPASS=%s sshpass -e %s" % (pw, sshcmd)

        p = subprocess.Popen(sshcmd, shell=True, stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE,
                                                 stdin=subprocess.PIPE)

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
        [p.terminate for p in procs if p.is_alive()]

    [p.join() for p in procs]

class CredException(Exception):
    pass

def establish_ssh_cred(user, host, port):
    """Make a test ssh connection to determine the password, if needed"""

    cmd = 'ssh -p %d %s@%s which splitcpy' % (port, user, host)
    password = None

    session = pexpect.spawn(cmd)
    while True:
        options = ['password:', 'splitcpy', pexpect.EOF, pexpect.TIMEOUT]
        match = session.expect(options)

        if match == 0:
            password = getpass.getpass(session.before + 'password:')
            session.sendline(password)
        elif match == 1:
            session.close()
            return password
        elif match == 2:
            raise CredException
        elif match == 3:
            raise CredException

def main():
    args = parse_args()

    if args.s:
        output_split(args.srcfile, args.num_slices, args.slice, args.bytes,
                         sys.stdout)
    else:
        try:
            user, host, path = parse_net_spec(args.srcfile)
            password = establish_ssh_cred(user, host, args.port)
            dl_file(args.srcfile, args.destfile, args.num_slices, args.slice_size, password, args.port)
        except CredException:
            print("Error establishing contact with remote splitcpy")
            sys.exit(-1)


if __name__ == '__main__':
    main()
