#!/usr/bin/python

from setuptools import setup
import splitcpy

setup(name='splitcpy',
      packages=['splitcpy'],
      version=splitcpy.__version__,
      description="Copy a remote file using multiple SSH streams",
      classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved ' +
            ':: GNU General Public License v2 or later (GPLv2+)',
            'Natural Language :: English',
            'Operating System :: POSIX',
            'Programming Language :: Python',
            'Topic :: Utilities',
      ],
      entry_points={
            'console_scripts': ['splitcpy=splitcpy.splitcpy:main'],
      },
      install_requires=['pexpect', ],
      tests_require=['funcsigs', 'mock', 'pytest'],
      author="David Steele",
      author_email="dsteele@gmail.com",
      url='https://github.com/davesteele/splitcpy',
      )
