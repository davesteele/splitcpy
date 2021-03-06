#!/usr/bin/python

import splitcpy
from mock import patch
import subprocess
import pytest
import tempfile
import os
import shutil


@patch('splitcpy.splitcpy.establish_ssh_cred',
       return_value=(None, {'version': splitcpy.__version__,
                            'entries': [[None, None, None, 'f1']]}))
@patch('splitcpy.splitcpy.dl_file')
def test_main_local_dl(dl_file, cred):

    cmd = "-n 5 -b 20 user@host:remotefile localfile"
    splitcpy.splitcpy.main(cmd.split())

    assert dl_file.called
    dl_file.assert_called_with('user@host:f1',
                               'localfile', 5, 20, None, 22)
    assert cred.called
    cred.assert_called_with('user', 'host', 22, ['remotefile'])


def test_main_remote_dl():
    with patch('splitcpy.splitcpy.output_split') as output_split:
        splitcpy.splitcpy.main("-s 1,0,1 localfile".split())

        assert output_split.called
#        output_split.assert_called_with('localfile', 1, 0, 10000)


@patch('splitcpy.splitcpy.establish_ssh_cred',
       side_effect=splitcpy.splitcpy.CredException)
@patch('splitcpy.splitcpy.sys.exit')
def test_main_cred_excep(exit, establish_cred):
    cmd = "-n 5 -b 20 user@host:remotefile localfile"
    splitcpy.splitcpy.main(cmd.split())

    assert exit.called
    assert exit.call_args[0][0] != 0
    assert isinstance(exit.call_args[0][0], int)


def test_that_last_line():
    path = splitcpy.__path__[0]
    cmd = "python %s/splitcpy.py -h" % path

    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    (out, err) = p.communicate()

    assert "usage:" in out.decode()


@pytest.fixture
def testdir(request):
    dir = tempfile.mkdtemp()

    request.addfinalizer(lambda: shutil.rmtree(dir))

    return dir


@patch('splitcpy.splitcpy.establish_ssh_cred',
       return_value=(None, {'version': splitcpy.__version__,
                            'entries': [[None, None, None, 'f1']]}))
@patch('splitcpy.splitcpy.dl_file')
def test_dest_dir(dl_file, cred, testdir):
    cmd = "-n 5 -b 20 user@host:remotefile " + testdir
    splitcpy.splitcpy.main(cmd.split())

    dl_file.assert_called_with('user@host:f1',
                               os.path.join(testdir, 'f1'),
                               5, 20, None, 22)


@pytest.mark.parametrize("low, high, rval", [
    ("0.0",   "100.100", 0),
    ("0.0",   "0.0",     1),
    ("100.0", "100.100", 1),
])
@patch('splitcpy.splitcpy.dl_file')
@patch('splitcpy.splitcpy.establish_ssh_cred',
       return_value=(None, {'version': splitcpy.__version__,
                            'entries': [[None, None, None, 'f1']]}))
@patch('splitcpy.splitcpy.sys.exit')
def test_ver_check_dl(exit, cred, dl_file, low, high, rval, monkeypatch):

    monkeypatch.setattr(splitcpy.splitcpy, "__VER_DL_MIN__", low)
    monkeypatch.setattr(splitcpy.splitcpy, "__VER_DL_MAX__", high)

    cmd = "-n 5 -b 20 user@host:remotefile localfile"
    splitcpy.splitcpy.main(cmd.split())

    if rval:
        assert exit.called
        assert exit.call_args[0][0] == rval
        assert isinstance(exit.call_args[0][0], int)
    else:
        assert not exit.called
