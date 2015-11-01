
import splitcpy
import os
import stat


def test_fifo():
    path = splitcpy.make_fifo()
    assert os.path.exists(path)
    assert stat.S_ISFIFO(os.stat(path).st_mode)

    splitcpy.del_fifo(path)
    assert not os.path.exists(path)
