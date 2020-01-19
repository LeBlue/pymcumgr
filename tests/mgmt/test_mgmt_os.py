import pytest
from pymcumgr.mgmt.os_cmd import CmdOS, Reset, Echo


_values_req = [
    # cmd_fn, cmd_args, hdr_bin, data_bin
    # reset
    ( CmdOS.reset, (), b'\x02\x00\x00\x00\x00\x00\x00\x05', b'\xa0'),
    # echo
    ( CmdOS.echo, ({'d': 'OK' },), b'\x02\x00\x00\x00\x00\x00\x00\x00', b'\xa1ad\xa1adbOK'),
    # echo
    ( CmdOS.echo, (
        {'d': 'Hallo'}, ),
        b'\x02\x00\x00\x00\x00\x00\x00\x00',
        b'\xa1ad\xa1adeHallo'
    ),
]

@pytest.mark.parametrize('cmd_fn,cmd_args,hdr_bin,data_bin',
    _values_req
)
def test_img_cmd(cmd_fn, cmd_args, hdr_bin, data_bin):
    cmd = cmd_fn(*cmd_args)

    hdr = cmd.hdr
    assert hdr != None

    hdr_enc = hdr.encode()
    # note: length field not set yet
    assert hdr_enc == hdr_bin

    cmd_enc = cmd.encode()

    assert cmd.hdr.length == len(data_bin)
    assert cmd_enc[hdr.size:] == data_bin