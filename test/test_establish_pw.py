
from mock import patch, Mock
import pytest
import splitcpy


def pexpect_session(val):
    sessionmock = Mock()
    sessionmock.expect.side_effect = val
    sessionmock.sendline.return_value = None
    sessionmock.before = 'foo {"'
    sessionmock.after = '": 0.3, "entries": ["f1", "f2"]} bar'

    return sessionmock


@patch('splitcpy.splitcpy.pexpect')
@patch('splitcpy.splitcpy.getpass.getpass', return_value='shhh')
@pytest.mark.parametrize(('val', 'cept', 'sendlines', 'tpw'), [
    ((0, 1),    False, 1, 'shhh'),
    ((0, 0, 1), False, 2, 'shhh'),
    ((1,),      False, 0, None),
    ((0, 2),    True,  0, None),
    ((0, 3),    True,  0, None),
    ((3,),      True,  0, None),
    ((4,),      True,  0, None),
])
def test_get_pw(getpass, pexpect, val, cept, sendlines, tpw):

    sessionmock = pexpect_session(val)
    pexpect.spawn.return_value = sessionmock

    if cept:
        with pytest.raises(splitcpy.splitcpy.CredException):
            pw = splitcpy.splitcpy.establish_ssh_cred('user', 'host', 22,
                                                      ['f1', 'f2'])
    else:
        pw, info = splitcpy.splitcpy.establish_ssh_cred('user', 'host', 22,
                                                        'thescript')

        assert pw == tpw
        assert sessionmock.sendline.call_count == sendlines
        assert sessionmock.expect.call_count == len(val)

    spawnarg = splitcpy.splitcpy.pexpect.spawn.call_args[0][0]
    assert 'user' in spawnarg
    assert 'host' in spawnarg
    assert '22' in spawnarg
