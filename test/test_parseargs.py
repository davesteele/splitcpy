#!/usr/bin/python

import splitcpy
import pytest
from mock import patch


@pytest.mark.parametrize("cmdstr", [
    "localfile localfile",
    "localfile user@host:remotefile",
    "user@host:remotefile user@host:remotefile",
    "-s 1 user@host:remotefile",
    "-s 1,1 user@host:remotefile",
    "-s 1,1,1 user@host:remotefile",
    "-s 1,0,0 user@host:remotefile",
    "-s 0,0,1 user@host:remotefile",
])
def test_parse_exception(cmdstr):
    with patch('splitcpy.splitcpy.sys.exit') as exit_mock:
        splitcpy.splitcpy.parse_args(cmdstr.split())
        assert exit_mock.called
        assert exit_mock.call_args[0][0] != 0
        assert isinstance(exit_mock.call_args[0][0], int)


@pytest.mark.parametrize("cmdstr", [
    "user@host:remotefile",
    "user@host:remotefile remotefile",
])
def test_parse_fileargs(cmdstr):
    with patch('splitcpy.splitcpy.sys.exit') as exit_mock:
        args = splitcpy.splitcpy.parse_args(cmdstr.split())
        assert not exit_mock.called
        assert args.srcfile == "user@host:remotefile"
        assert args.destfile == "remotefile"


@pytest.mark.parametrize(("spec", "user", "host", "path", "isnet"), [
    ("user@host:path", "user", "host", "path", True),
    ("host:path", None, None, "host:path", False),
    ("user@host", None, None, "user@host", False),
    ("path", None, None, "path", False),
])
def test_parse_net_spec(spec, user, host, path, isnet):
    assert (user, host, path) == splitcpy.splitcpy.parse_net_spec(spec)
    assert isnet == splitcpy.splitcpy.is_net_spec(spec)
