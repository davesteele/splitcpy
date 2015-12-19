#!/usr/bin/python

from setuptools import setup, Command
import splitcpy
import sys
import os
import shutil

from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as InstallCommand
from setuptools.command.build_py import build_py as BuildCommand


package = "splitcpy"

podir = "po"
pos = [x for x in os.listdir(podir) if x[-3:] == ".po"]
langs = sorted([os.path.split(x)[-1][:-3] for x in pos])


def modir(lang):
    mobase = "build/mo"
    return os.path.join(mobase, lang)


def mkmo(lang):
    outpath = modir(lang)
    if os.path.exists(outpath):
        shutil.rmtree(outpath)
    os.makedirs(outpath)

    inpath = os.path.join(podir, lang + ".po")

    cmd = "msgfmt %s -o %s/%s.mo" % (inpath, outpath, package)

    os.system(cmd)


def merge_i18n():
    cmd = "LC_ALL=C intltool-merge -u -c ./po/.intltool-merge-cache ./po "
    for infile in (x[:-3] for x in os.listdir('.') if x[-3:] == '.in'):
        print("Processing %s.in to %s" % (infile, infile))

        if 'desktop' in infile:
            flag = '-d'
        elif 'schema' in infile:
            flag = '-s'
        elif 'xml' in infile:
            flag = '-x'
        else:
            flag = ''

        if flag:
            os.system("%s %s %s.in %s" % (cmd, flag, infile, infile))


class MyBuildCommand(BuildCommand):
    def run(self, *args):
        BuildCommand.run(self, *args)

        for lang in langs:
            mkmo(lang)

        merge_i18n()


def polist():
    tmpl = "share/locale/%s/LC_MESSAGES/"
    modir('foo')
    polist = [(tmpl % x, ["%s/%s.mo" % (modir(x), package)]) for x in langs]

    return polist


class BuildI18n(Command):
    """PO file creation/update"""

    description = "Create/update POT and PO files"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("Creating POT file")
        cmd = "cd po; intltool-update --pot --gettext-package=%s" % package
        os.system(cmd)

        for lang in langs:
            print("Updating %s PO file" % lang)
            cmd = "cd po; intltool-update --dist \
                   --gettext-package=%s %s >/dev/null 2>&1" % (package, lang)
            os.system(cmd)


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
      packages=[package],
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
          'build_i18n': BuildI18n,
          'build_py': MyBuildCommand,
      },
      data_files=polist(),
      author="David Steele",
      author_email="dsteele@gmail.com",
      url='https://davesteele.github.io/splitcpy/',
      )
