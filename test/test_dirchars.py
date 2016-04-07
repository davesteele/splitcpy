
import pytest
import os
import json
import subprocess
import sys

import splitcpy


@pytest.fixture(params=[
    'fnormalfile',
    'ffilewith[openbrace[',
    'ffilewith.dot.',
    'ffilewith]closebrace]',
    'ffilewith space',
    'ffilewith-dash',
])
def tstfile(request, tmpdir):
    path = os.path.join(tmpdir.__str__(), request.param)

    with open(path, 'w') as fp:
        fp.write('hi')

    return path


@pytest.mark.parametrize('wildcard', (False, True))
@pytest.mark.parametrize('external', (False, True))
def test_dirnames(tstfile, external, wildcard):
    filename = os.path.split(tstfile)[-1]
    basepath = os.path.split(tstfile)[:-1][0]

    query = splitcpy.quote_path(tstfile)
    if wildcard:
        query = os.path.join(basepath, filename[0] + '\*')

    if external:
        major, minor = sys.version_info[0:2]
        cmd = "python%d.%d -m splitcpy -f %s" % (major, minor, query)
        statinfo = subprocess.check_output(cmd, shell=True).decode()
    else:
        statinfo = json.dumps(splitcpy.eval_files([tstfile]))

    assert filename in statinfo


@pytest.mark.parametrize('test, result', (
    ('a*b', 'a\\*b'),
    ('a b', 'a\ b'),
    ('a]b', 'a\]b'),
    ('a#b', 'a\#b'),
    ('a;b', 'a\;b'),
    ('a&b', 'a\&b'),
    ('a,b', 'a\,b'),
    ('a?b', 'a\\?b'),
    ('a$b', 'a\$b'),

    ('a**b', 'a\\*\\*b'),
    ('a*b*', 'a\*b\*'),
))
def test_quote_path(test, result):
    assert splitcpy.quote_path(test) == result
