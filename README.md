# splitcpy

<a href="https://davesteele.github.io/splitcpy/">Home Page</a>

Copy files remotely using multiple streams

Avoid traffic shaping of individual TCP streams by copying over multiple
streams.

Install the script into the path on both the local and remote computer.

This is currently only supports downloading files.

Note that _splitcpy_ requires _sshpass_ if sites are
being accessed that require an ssh password.

## Usage

    $ splitcpy.py -h
    usage: splitcpy.py [user]@host:path [path]
           splitcpy.py [user]@host:path [...] [dir]
    
    Copy a remote file using multiple SSH streams.
    
    positional arguments:
      path        filename, with optional path
      dir         directory name (file name taken from source path)
    
    optional arguments:
      -h, --help  show this help message and exit
      -s n,i,l    (internal use only) Generate file interleave of 'l' bytes for
                  the 'i'th slice out of 'n'
      -f          (internal use only) Output far-side wildcard information
      -p port     ssh port to use (if not the default)
      -n num      number of parallel slices to run (default=10)
      -b bytes    chunk size for slices (default=10,000)
    
    The source file is remote. Remote files are specified as e.g.
    [user@]host:path. 'splitcpy' must be installed on both the local and remote
    hosts.


[![Build Status](https://travis-ci.org/davesteele/splitcpy.svg?branch=master)](https://travis-ci.org/davesteele/splitcpy) [![Coverage Status](https://coveralls.io/repos/davesteele/splitcpy/badge.svg?branch=master&service=github)](https://coveralls.io/github/davesteele/splitcpy?branch=master)
