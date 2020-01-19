
import pytest
from pymcumgr.mgmt.img_cmd import CmdImg, ImageList, ImageTest, ImageConfirm


_img_hash_array_1 = [
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
]

_values_req = [
    # cmd_fn, cmd_args, hdr_bin, data_bin
    # image list
    ( CmdImg.getState, (), b'\x00\x00\x00\x00\x00\x01\x00\x00', b'\xa0'),
    # image confirm
    ( CmdImg.setState, ({'confirm': True },), b'\x02\x00\x00\x00\x00\x01\x00\x00', b'\xa1gconfirm\xf5'),
    # image test
    ( CmdImg.setState, (
        {'confirm': False, 'hash': bytes(_img_hash_array_1) },),
        b'\x02\x00\x00\x00\x00\x01\x00\x00',
        b'\xa2gconfirm\xf4dhashX ' +
        bytes(_img_hash_array_1)
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



@pytest.mark.parametrize('cmd_fn,cmd_args,cmd_dict', [
    (ImageList, (), {}),
    (ImageTest, ("9f429f57afdb81a090ac5afb13a1e17352b28d7b475e5c96b70ebc603c01fcc3" ,),
        { 'confirm': False,
        'hash': b'\x9fB\x9fW\xaf\xdb\x81\xa0\x90\xacZ\xfb\x13\xa1\xe1sR\xb2\x8d{G^\\\x96\xb7\x0e\xbc`<\x01\xfc\xc3'}),
    (ImageConfirm, (),  { 'confirm': True }),

])
def test_img_cmd_handler(cmd_fn, cmd_args, cmd_dict):
    cmd = cmd_fn(*cmd_args)

    msg = cmd.message()
    enc_msg = msg.encode(seq=0)
    assert msg.payload_dict == cmd_dict
    assert msg.payload_bytes != b''
    assert msg.hdr != None

    msg1 = cmd.message()

    assert msg1.encode(seq=0) == enc_msg

    # assert cmd.hdr.length == len(data_bin)
    # assert cmd_enc[hdr.size:] == data_bin

# _values_rsp = [
#     # cmd_rsp_fn, rsp_bin, rsp_obj
#     ( CmdImg.imageListCompleted, b'\x01\x00\x00\x01\x00\x01\x00\x00\xa0', {}),
#     ( CmdImg.getStateCompleted, b'\x03\x00\x00\x00\x00\x01\x00\x00\xa0', {}),
# ]

# @pytest.mark.parametrize('cmd_rsp_fn,rsp_bin,rsp_obj',
#     _values_rsp
# )
# def test_img_cmd_rsp(cmd_rsp_fn, rsp_bin, rsp_obj):

#     cmd = cmd_rsp_fn(rsp_bin)

#     assert cmd is not None
#     assert cmd.payload_dict == rsp_obj
