from enum import Enum

from .header import MgmtHeader, MgmtGroup, MgmtOp, CmdBase, RequestBase
from .cborattr import CborAttr

class MgmtIdOS(Enum):
    ECHO           = 0
    CONS_ECHO_CTRL = 1
    TASKSTAT       = 2
    MPSTAT         = 3
    DATETIME_STR   = 4
    RESET          = 5


class CmdOS(CmdBase):

    _group = MgmtGroup.OS
    _group.registerGroupIDs(MgmtIdOS)


    @staticmethod
    def echo(echo_str, seq=0):
        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.OS, MgmtIdOS.ECHO, seq=seq)
        return CmdOS(hdr, {'d': echo_str})
        #return CmdOS._encode(hdr, {'d': echo_str}, seq=seq)

    @staticmethod
    def reset(seq=0):
        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.OS, MgmtIdOS.RESET, seq=seq)
        return CmdOS(hdr, {})
        #return CmdOS._encode(hdr, {}, seq=seq)

    @staticmethod
    def cons_echo_ctrl(seq=0):
        raise NotImplementedError('cons_echo_ctrl')

    @staticmethod
    def taskstat(seq=0):
        raise NotImplementedError('cons_echo_ctrl')


class Echo(RequestBase):

    def __init__(self, text):
        super().__init__()
        self.text = text

    def message(self):
        if not self.response_data:
            return CmdOS.echo(self.text)
        return None

    def parse_response(self, rsp):
        hdr = MgmtHeader.decode(rsp)
        if hdr.op != MgmtOp.WRITE_RSP or hdr.group != MgmtGroup.OS or hdr.id != MgmtIdOS.ECHO:
            raise ValueError('Not a echo command response: {}'.format(str(hdr)))

        if len(rsp) > hdr.size:
            dec_msg = CborAttr.decode(rsp[hdr.size:])
            print(dec_msg)
        self.response_data = dec_msg
        return self.response_data

class Reset(RequestBase):

    # def __init__(self):
    #     super().__init__()

    def message(self):
        if not self.response_data:
            return CmdOS.reset()
        return None

    def parse_response(self, rsp):
        hdr = MgmtHeader.decode(rsp)
        if hdr.op != MgmtOp.WRITE_RSP or hdr.group != MgmtGroup.OS or hdr.id != MgmtIdOS.RESET:
            raise ValueError('Not a reset command response: {}'.format(str(hdr)))

        if len(rsp) > hdr.size:
            dec_msg = CborAttr.decode(rsp[hdr.size:])
            print(dec_msg)
        self.response_data = dec_msg

def registerOSCommandArguments(sub_parsers):

    # ECHO
    echo_parser = sub_parsers.add_parser('echo', help='Send data to a device and display the echoed back data')
    echo_parser.add_argument('text', type=str, default=None)

    # RESET
    sub_parsers.add_parser('reset', help='Perform a soft reset of a device')


    return sub_parsers

