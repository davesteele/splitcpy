# splitcpy
Copy files remotely using multiple streams

Avoid traffic shaping of individual TCP streams by copying over multiple
streams.

Install the script into the path on both the local and remote computer.

This is currently demonstration quality.

## Usage

    $ ./splitcpy.py -h
    usage: splitcpy.py [-h] [-s n,i,l] [-p port] [-n num] [-b bytes]
                       srcfile [destfile]
    
    Copy a remote file using multiple SSH streams.
    
    positional arguments:
      srcfile     Source file
      destfile    Destination file
    
    optional arguments:
      -h, --help  show this help message and exit
      -s n,i,l    Generate file interleave of 'l' bytes for the 'i'th slice out of
                  'n'(internal use only)
      -p port     ssh port to use (if not the default)
      -n num      number of parallel slices to run (default=10)
      -b bytes    chunk size for slices (default=10,000)
    
    The source file is remote. Remote files are specified as e.g. user@host:path.

