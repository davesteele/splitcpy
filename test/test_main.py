#!/usr/bin/python

import splitcpy
from mock import patch

def test_main_local_dl():

    with patch('splitcpy.splitcpy.establish_ssh_cred', return_value=None) as cred:
        with patch('splitcpy.splitcpy.dl_file') as dl_file:
            splitcpy.splitcpy.main("-n 5 -b 20 user@host:remotefile localfile".split())

            assert dl_file.called
            dl_file.assert_called_with('user@host:remotefile', 'localfile', 5, 20, None, 22)
            assert cred.calld
            cred.assert_called_with('user', 'host', 22)

def test_main_remote_dl():
    with patch('splitcpy.splitcpy.output_split') as output_split:
        splitcpy.splitcpy.main("-s 1,0,1 localfile".split())

        assert output_split.called
#        output_split.assert_called_with('localfile', 1, 0, 10000)


