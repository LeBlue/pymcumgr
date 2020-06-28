
from enum import Enum
import sys

'''
/** Opcodes; encoded in first byte of header. */
#define MGMT_OP_READ            0
#define MGMT_OP_READ_RSP        1
#define MGMT_OP_WRITE           2
#define MGMT_OP_WRITE_RSP       3
'''
class MgmtOp(Enum):
    READ      = 0
    READ_RSP  = 1
    WRITE     = 2
    WRITE_RSP = 3



'''
/**
 * The first 64 groups are reserved for system level mcumgr commands.
 * Per-user commands are then defined after group 64.
 */
#define MGMT_GROUP_ID_OS        0
#define MGMT_GROUP_ID_IMAGE     1
#define MGMT_GROUP_ID_STAT      2
#define MGMT_GROUP_ID_CONFIG    3
#define MGMT_GROUP_ID_LOG       4
#define MGMT_GROUP_ID_CRASH     5
#define MGMT_GROUP_ID_SPLIT     6
#define MGMT_GROUP_ID_RUN       7
#define MGMT_GROUP_ID_FS        8
#define MGMT_GROUP_ID_PERUSER   64
'''
_registered_groups = []

class MgmtGroup(Enum):
    OS     = 0
    IMAGE  = 1
    STAT   = 2
    CONFIG = 3
    LOG    = 4
    CRASH  = 5
    SPLIT  = 6
    RUN    = 7
    FS     = 8
    PERUSER = 64




    def registerGroupIDs(self, id_enum):
        while self.value >= len(_registered_groups):
            _registered_groups.append(None)

        _registered_groups[self.value] = id_enum

    def getId(self, nh_id):
        if len(_registered_groups) <= self.value:
            return None

        return _registered_groups[self.value](nh_id)



'''
/**
 * mcumgr error codes.
 */
#define MGMT_ERR_EOK            0
#define MGMT_ERR_EUNKNOWN       1
#define MGMT_ERR_ENOMEM         2
#define MGMT_ERR_EINVAL         3
#define MGMT_ERR_ETIMEOUT       4
#define MGMT_ERR_ENOENT         5
#define MGMT_ERR_EBADSTATE      6       /* Current state disallows command. */
#define MGMT_ERR_EMSGSIZE       7       /* Response too large. */
#define MGMT_ERR_ENOTSUP        8       /* Command not supported. */
#define MGMT_ERR_EPERUSER       256
'''
class MgmtErr(Enum):
    EOK       = 0
    EUNKNOWN  = 1
    ENOMEM    = 2
    EINVAL    = 3
    ETIMEOUT  = 4
    ENOENT    = 5
    EBADSTATE = 6       #/* Current state disallows command. */
    EMSGSIZE  = 7       #/* Response too large. */
    ENOTSUP   = 8       #/* Command not supported. */
    EPERUSER  = 256

    def __bool__(self):
        if self.value == 0:
            return False
        return True

    @staticmethod
    def from_response(rsp, allow_missing=False):
        if not 'rc' in rsp:
            if allow_missing:
                return MgmtErr.EOK
            return MgmtErr.EUNKNOWN
            #raise ValueError('Missing Mgmt return code in payload: {}'.format(str(rsp)))
        rc = rsp['rc']
        try:
            return MgmtErr(rc)
        except ValueError as e:
            return MgmtErr.EUNKNOWN
                #raise ValueError('Invalid MgmtErr code in payload: {}'.format(str(rsp)))
        return MgmtErr.EUNKNOWN


'''
#define MGMT_HDR_SIZE           8

struct mgmt_hdr {
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    uint8_t  nh_op:3;           /* MGMT_OP_[...] */
    uint8_t  _res1:5;
#endif
#if __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    uint8_t  _res1:5;
    uint8_t  nh_op:3;           /* MGMT_OP_[...] */
#endif
    uint8_t  nh_flags;          /* Reserved for future flags */
    uint16_t nh_len;            /* Length of the payload */
    uint16_t nh_group;          /* MGMT_GROUP_ID_[...] */
    uint8_t  nh_seq;            /* Sequence number */
    uint8_t  nh_id;             /* Message ID within group */
};
'''
from struct import pack, unpack_from

class MgmtHeader(object):

    fmt = '!BBHHBB'
    size = 8

    @staticmethod
    def decode(b):
        t = unpack_from(MgmtHeader.fmt, b)
        return MgmtHeader(t[0], t[3], t[5], length=t[2], seq=t[4], flags=t[1])

    def __init__(self, op, group, nh_id, length=0, seq=0, flags=0):
        self.op = MgmtOp(op)
        self.flags = flags
        self.length = length
        self.group = MgmtGroup(group)
        self.seq = seq
        self.id = self.group.getId(nh_id)
        if self.id is None:
            try:
                self.id = nh_id.value
            except AttributeError:
                self.id = nh_id


    def encode(self):
        try:
            id = self.id.value
        except AttributeError:
            id = self.id
        return pack(MgmtHeader.fmt,
            self.op.value,
            self.flags,
            self.length,
            self.group.value,
            self.seq,
            id
        )

    def __str__(self):
        return '{}(op:{} group:{} id:{} len:{} seq:{} flags:{})'.format(self.__class__.__name__,
            self.op, self.group, self.id, self.length, self.seq, self.flags)

from .cborattr import CborAttr

class RequestBase(object):
    '''object keeps state of request'''

    _debug = False

    @classmethod
    def set_debug(cls, enable):
        cls._debug = enable

    def __init__(self):
        self.response_data = None

    def response_header(self, rsp):
        '''
        return parsed header object for length/partial packet detection
        '''
        return CmdBase.decode_header(rsp)

    def parse_response(self, rsp):
        '''
        parameter rsp, bytes of response, guaranteed to have required bytes according to header (reassembled)
        tracks current state of request,
        return valid ResponseBase or inherited object
        '''
        raise NotImplementedError('Must be provided by subclass')

    def message(self):
        '''
        return the current request message of CmdBase subtype, or None if request is already completed
        '''
        raise NotImplementedError('Must be provided by subclass')

    def __str__(self):
        return '{}()'.format(self.__class__.__name__)

class CmdBase(object):

    _group = None
    _debug = False

    @classmethod
    def set_debug(cls, enable):
        cls._debug = enable

    def __init__(self, hdr, payload_dict=None, payload_bytes=None, response_cb=None):
        self.hdr = hdr
        self.payload_dict = payload_dict
        if payload_bytes is not None:
            if len(payload_bytes) > hdr.length:
                raise ValueError(
                    'Too many payload bytes: {} for {}'.format(len(payload_bytes), str(hdr))
                )
            elif len(payload_bytes) < hdr.length:
                raise ValueError('Too few payload bytes: {} for {}'.format(len(payload_bytes), str(hdr)))
        self.payload_bytes = payload_bytes
        self.response_cb = response_cb

    def encode(self, seq=0):
        '''encodes self.payload_dict and header
        returns both as bytes
        '''
        self.payload_bytes = CborAttr.encode(self.payload_dict)

        self.hdr.seq = seq
        self.hdr.length = len(self.payload_bytes)

        return self.hdr.encode() + self.payload_bytes

    def decode(self):
        if len(self.payload_bytes) < self.hdr.length:
            raise ValueError('Too few payload bytes: {} got: {}'.format(str(self.hdr), len(self.payload_bytes)))
        self.payload_dict = CborAttr.decode(self.payload_bytes)[0]

        return self.payload_dict

    @classmethod
    def decode_header(cls, rsp):
        if cls._debug:
            print('Decode common: ', rsp)

        if len(rsp) < MgmtHeader.size:
            return cls(None)
        try:
            hdr = MgmtHeader.decode(rsp)
        except Exception as e:
            print('Decode common header failed', file=sys.stderr)
            raise ValueError('Invalid Header: {}'.format(str(e)))

        if len(rsp[hdr.size:]) < hdr.length:
            return cls(hdr)

        if hdr.op != MgmtOp.WRITE_RSP and hdr.op != MgmtOp.READ_RSP:
            raise ValueError('Not a response: {}'.format(str(MgmtOp(hdr.op))))

        return cls(hdr, payload_bytes=rsp[hdr.size:])


    def __str__(self):
        return '{} {}'.format(str(self.hdr), str(self.payload_dict))

class ResponseBase(object):

    _debug = False

    def __init__(self, err, rsp_data, rsp_obj=None):
        if not isinstance(err, MgmtErr):
            raise ValueError('First argment must be MgmtErr')
        self.err = err
        self.data = rsp_data
        self.obj = rsp_obj

    def __str__(self):
        return 'Response({},{})'.format(str(self.err), str(self.obj) if self.obj else str(self.data))
