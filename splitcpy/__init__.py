#!/usr/bin/python

from .version import __version__
from .splitcpy import make_fifo, del_fifo, dl_slice, dl_file, output_split


splitcpy.__version__ = __version__
