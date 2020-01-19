
import pytest
from pymcumgr.mgmt.header import MgmtHeader, MgmtOp, MgmtGroup
from pymcumgr.mgmt.img_cmd import MgmtIdImg


_header_values = [
        (MgmtOp.READ,      MgmtGroup.IMAGE, MgmtIdImg.STATE, 0, b'\x00\x00\x00\x00\x00\x01\x00\x00'),
        (MgmtOp.READ_RSP,  MgmtGroup.IMAGE, MgmtIdImg.STATE, 0, b'\x01\x00\x00\x00\x00\x01\x00\x00'),
        (MgmtOp.WRITE,     MgmtGroup.IMAGE, MgmtIdImg.STATE, 0, b'\x02\x00\x00\x00\x00\x01\x00\x00'),
        (MgmtOp.WRITE_RSP, MgmtGroup.IMAGE, MgmtIdImg.STATE, 0, b'\x03\x00\x00\x00\x00\x01\x00\x00'),
    ]





@pytest.mark.parametrize('op,group,id,seq,bin',
    _header_values
)
def test_header_encode(op, group, id, seq, bin):

    hdr = MgmtHeader(op, group, id, seq=seq)
    assert hdr != None

    hdr_enc = hdr.encode()
    # note: length field not set yet
    assert hdr_enc == bin


@pytest.mark.parametrize('op,group,id,seq,bin',
    _header_values
)
def test_header_decode(op, group, id, seq, bin):

    hdr = MgmtHeader.decode(bin)
    assert hdr != None

    assert 0 == hdr.length
    assert op == hdr.op
    assert group == hdr.group
    assert id == hdr.id
    assert seq == hdr.seq


