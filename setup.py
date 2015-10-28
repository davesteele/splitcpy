#!/usr/bin/python

from setuptools import setup
import splitcpy
import sys
import os

from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as InstallCommand


class MyInstall(InstallCommand):
    def run(self):
        found = False
        for path in os.environ["PATH"].split(os.pathsep):
            if os.path.exists(os.path.join(path, 'sshpass')):
                found = True

        if not found:
            print(
                "WARNING - "
                "'sshpass' must be installed to support ssh passwords"
            )

        InstallCommand.run(self)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
#        self.test_args = []
#        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

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
      tests_require=['pytest', 'mock'],
      cmdclass={
          'test': PyTest,
          'install': MyInstall,
      },
      author="David Steele",
      author_email="dsteele@gmail.com",
      url='https://davesteele.github.io/splitcpy/',
      )
