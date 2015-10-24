
import tempfile
import pytest
import shutil
import os
import json
from collections import namedtuple
from mock import patch

import splitcpy

FSpec = namedtuple('FSpec', ['type', 'readable', 'writeable', 'path'])


def touch(fname, readable=True, writeable=True):
    with open(fname, 'a'):
        pass

    perms = 0000

    if readable:
        perms |= 292    # octal 0444
    if writeable:
        perms |= 146    # octal 0222

    os.chmod(fname, perms)


@pytest.fixture
def testdir(request):
    dir = tempfile.mkdtemp()

    adir = os.path.join(dir, 'adir')
    bdir = os.path.join(dir, 'bdir')

    os.mkdir(os.path.join(dir, 'adir'))
    os.mkdir(os.path.join(dir, 'bdir'))

    touch(os.path.join(adir, 'one.txt'))
    touch(os.path.join(adir, 'two'))
    touch(os.path.join(bdir, 'one.doc'))

    touch(os.path.join(dir, 'noread'), readable=False)
    touch(os.path.join(dir, 'nowrite'), writeable=False)

    def fin():
        shutil.rmtree(dir)

    request.addfinalizer(fin)

    return dir


def test_tmpdir(testdir):
    assert(os.path.exists(testdir))
    assert(os.path.exists(os.path.join(testdir, 'adir')))

    assert(os.access(os.path.join(testdir, 'noread'), os.W_OK))
    assert(not os.access(os.path.join(testdir, 'noread'), os.R_OK))

    assert(os.access(os.path.join(testdir, 'nowrite'), os.R_OK))
    assert(not os.access(os.path.join(testdir, 'nowrite'), os.W_OK))


def test_eval_version():
    info = splitcpy.splitcpy.eval_files(['*'])

    assert(info['version'] == splitcpy.__version__)


@pytest.mark.parametrize("spec, type", [
    ('adir', 'd'),
    ('noread', 'f'),
])
def test_eval_type(testdir, spec, type):

    info = splitcpy.splitcpy.eval_files([os.path.join(testdir, spec)])

    assert(len(info['entries']) == 1)

    fspec = FSpec(*info['entries'][0])
    assert(fspec.type == type)


@pytest.mark.parametrize("wildcards, num, expected", [
    ('*/*', 3, ['one.txt', 'two', 'one.doc']),
    ('*/one*', 2, ['one.txt', 'one.doc']),
    ('*/three*', 0, []),
])
def test_eval_wildcard(testdir, wildcards, num, expected):

    fullwild = [os.path.join(testdir, x) for x in wildcards.split()]

    info = splitcpy.splitcpy.eval_files(fullwild)

    assert(len(info['entries']) == num)

    entries = [FSpec(*x) for x in info['entries']]
    for entry in entries:
        assert(any([x in entry.path for x in expected]))


@pytest.mark.parametrize("spec, readable, writeable", [
    ('noread', False, True),
    ('nowrite', True, False),
    ('adir', True, True),
])
def test_eval_perms(testdir, spec, readable, writeable):

    info = splitcpy.splitcpy.eval_files([os.path.join(testdir, spec)])
    fspec = FSpec(*info['entries'][0])

    assert(fspec.readable == readable)
    assert(fspec.writeable == writeable)


def test_eval_main(capsys, testdir):

    path = os.path.join(testdir, 'noread')

    splitcpy.splitcpy.main(['-f', path])
    out, err = capsys.readouterr()
    cmdinfo = json.loads(out)

    localinfo = splitcpy.splitcpy.eval_files([path])

    assert(cmdinfo == localinfo)
