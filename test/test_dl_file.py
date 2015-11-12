

from mock import patch, Mock
import pytest
import tempfile
import os

import splitcpy


filesize = 0


@pytest.fixture(params=[128, 256])
def testfile(request):

    request.module.filesize = request.param

    (fd, path) = tempfile.mkstemp()

    with open(path, 'wb') as fp:
        fp.write(bytearray(range(request.param)))

    request.addfinalizer(lambda: os.unlink(path))

    return path


@patch('splitcpy.splitcpy.Queue')
@patch('splitcpy.splitcpy.Process', return_value=Mock())
def test_dl_file(process, queue, testfile):

    queue0 = Mock()
    queue0.get.return_value = bytearray([0x01])
    queue1 = Mock()
    queue1.get.return_value = None
    splitcpy.splitcpy.Queue.side_effect = [queue0, queue1]

    splitcpy.dl_file('src', testfile, 2, 1, None, 22)


@patch('splitcpy.splitcpy.subprocess.Popen')
@patch('splitcpy.splitcpy.make_fifo')
@patch('splitcpy.splitcpy.del_fifo')
def test_dl_slice(del_fifo, mkfifo, process, testfile):

    processmock = Mock()
    processmock.poll.return_value = None
    process.return_value = processmock

    mkfifo.return_value = testfile

    queue = Mock()

    splitcpy.dl_slice('user@host:file', 2, 0, 1, queue, 'shhh', 22)

    assert processmock.poll.called
    assert queue.put.call_count == filesize + 1
    assert processmock.kill.called
    assert mkfifo.call_count == 1
    assert del_fifo.call_count == 1
