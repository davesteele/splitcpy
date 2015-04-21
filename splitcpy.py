#!/usr/bin/python

import argparse
import sys
import re
from multiprocessing import Process, Queue
import subprocess


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
                epilog="The source file is remote.",
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
        parser.print_usage()
        print "Invalid interleave argument"
        sys.exit(1)

    if not args.s and (not is_net_spec(args.srcfile)
                       or is_net_spec(args.destfile)):
        parser.print_usage()
        print "Currently only supports download copying"
        sys.exit(1)

    if not args.s and not args.destfile:
        parser.print_usage()
        print "Must specify destination file"
        sys.exit(1)

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
    with open(srcfile, 'r') as src:
        for pkt in slice_iter(src, num_slices, slice, bytes):
            dst.write(pkt)

def dl_slice(src_spec, num_slices, slice, bytes, queue):
    """Call a remote interleave slice of a file to download"""
    src_file = parse_net_spec(src_spec)[2]

    cmd = "./splitcpy.py %s -s %d,%d,%d" % (src_file, num_slices, slice, bytes)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    while True:
        buf = p.stdout.read(bytes)
        if not buf:
            break
        queue.put(buf)

    queue.put(None)


def dl_file(src, dest, num_slices, bytes):
    """Perform a parallel download of a file"""
    qs = [Queue(10) for x in range(num_slices)]
    procs = [Process(target=dl_slice, args=(src, num_slices, x, bytes, qs[x]))
                for x in range(num_slices)]
    [p.start() for p in procs]

    with open(dest, 'w') as dfp:
        done = False
        while not done:
            for i in range(num_slices):
                buf = qs[i].get()
                if buf is None:
                    done = True
                else:
                    dfp.write(buf)

    [p.join() for p in procs]

def main():
    args = parse_args()

    if args.s:
        output_split(args.srcfile, args.num_slices, args.slice, args.bytes,
                         sys.stdout)
    else:
        dl_file(args.srcfile, args.destfile, 2, 1)


main()
