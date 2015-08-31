#!/usr/bin/python

import splitcpy
from mock import patch
import os
import subprocess


def test_main_local_dl():

    with patch('splitcpy.splitcpy.establish_ssh_cred',
               return_value=None) as cred:
        with patch('splitcpy.splitcpy.dl_file') as dl_file:
            cmd = "-n 5 -b 20 user@host:remotefile localfile"
            splitcpy.splitcpy.main(cmd.split())

            assert dl_file.called
            dl_file.assert_called_with('user@host:remotefile',
                                       'localfile', 5, 20, None, 22)
            assert cred.called
            cred.assert_called_with('user', 'host', 22)


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
