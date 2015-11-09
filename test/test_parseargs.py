#!/usr/bin/python

import splitcpy
import pytest
from mock import patch
import getpass


@pytest.mark.parametrize("cmdstr", [
    "localfile localfile",
    "localfile user@host:remotefile",
    "u1@h:path u2@h:path",
    "u@h1:path u@h2:path",
    "-s 1 user@host:remotefile",
    "-s 1,1 user@host:remotefile",
    "-s 1,1,1 user@host:remotefile",
    "-s 1,0,0 user@host:remotefile",
    "-s 0,0,1 user@host:remotefile",
    "",
    "u@h:p localfile localdest",
])
@patch('splitcpy.splitcpy.sys.exit')
def test_parse_exception(exit_mock, cmdstr):
    splitcpy.splitcpy.parse_args(cmdstr.split())
    assert exit_mock.called
    assert exit_mock.call_args[0][0] != 0
    assert isinstance(exit_mock.call_args[0][0], int)


@pytest.mark.parametrize("cmdstr, srclist, dest", [
    ("h:f1", ['h:f1'], '.'),
    ("h:f1 dest", ['h:f1'], 'dest'),
    ("h:f1 h:f2", ['h:f1', 'h:f2'], '.'),
    ("h:f1 h:f2 dest", ['h:f1', 'h:f2'], 'dest'),
])
@patch('splitcpy.splitcpy.sys.exit')
def test_parse_fileargs(exit_mock, cmdstr, srclist, dest):
    args = splitcpy.splitcpy.parse_args(cmdstr.split())

    assert not exit_mock.called
    assert(args.rawsrcs == srclist)
    assert(args.rawdest == dest)


@pytest.mark.parametrize(("spec", "user", "host", "path", "isnet"), [
    ("user@host:path", "user", "host", "path", True),
    ("host:path", getpass.getuser(), "host", "path", True),
    ("user@host", None, None, "user@host", False),
    ("path", None, None, "path", False),
])
def test_parse_net_spec(spec, user, host, path, isnet):
    assert (user, host, path) == splitcpy.splitcpy.parse_net_spec(spec)
    assert isnet == splitcpy.splitcpy.is_net_spec(spec)
