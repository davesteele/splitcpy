
import pytest
from mock import Mock
import tempfile
import os

import splitcpy


@pytest.fixture()
def testfile(request):

    data = bytearray(range(256))

    (fd, path) = tempfile.mkstemp()
    with open(path, 'wb') as fp:
        fp.write(data)

    request.addfinalizer(lambda : os.unlink(path))

    return path


def test_ld_send_sz_1(testfile):
    dst = Mock()

    splitcpy.output_split(testfile, 2, 0, 1, dst)

    assert dst.write.call_count == 256 / 2
