from enum import Enum
from .header import MgmtHeader, MgmtGroup, MgmtOp, MgmtErr, CmdBase, RequestBase
from .cborattr import CborAttr

import sys

class MgmtIdImg(Enum):
    STATE    = 0
    UPLOAD   = 1
    FILE     = 2
    CORELIST = 3
    CORELOAD = 4
    ERASE    = 5

class SlotDescription(object):

    _flags = ('confirmed', 'pending', 'active', 'permanent')
    def __init__(self, slot_obj):
        try:

            self.slot = slot_obj['slot']
            self.version = slot_obj['version']
            self.hash = slot_obj['hash'].hex()
            self.bootable = slot_obj['bootable']
            self.confirmed = slot_obj['confirmed']
            self.pending = slot_obj['pending']
            self.active = slot_obj['active']
            self.permanent = slot_obj['permanent']


        except KeyError as e:
            raise KeyError('key {} expected'.format(str(e))) from None


    def __str__(self):
        flags = ','.join([
            flag for flag in self._flags if getattr(self, flag)
        ])
        return 'slot:{} version:{} hash:{} bootable:{} flags:{}'.format(
            self.slot, self.version, self.hash, 'true' if self.bootable else 'false', flags
        )
    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, str(self))

class ImgDescription(object):

    def __init__(self, obj):

        self.slots = []
        if not 'images' in obj:
            raise ValueError('key \'images\' expected')

        images = obj['images']

        if not isinstance(images, list):
            raise ValueError('list expected for key \'images\'')

        for slot in images:
            self.slots.append(SlotDescription(slot))


    def active_slot(self):
        for s in self.slots:
            if s.active:
                return s
        return None

    def confirmed_slot(self):
        for s in self.slots:
            if s.confirmed:
                return s
        return None

    def pending_slot(self):
        for s in self.slots:
            if s.pending:
                return s
        return None

    def other_slot(self):
        for s in self.slots:
            if not s.active:
                return s
        return None

    def state_sane(self):
        for s in self.slots:
            if (s.active and not s.confirmed) or (not s.active and s.confirmed) or s.pending:
                return False

        return True


    def __str__(self):
        return str(self.slots)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, str(self))



class CmdImg(CmdBase):

    _group = MgmtGroup.IMAGE
    _group.registerGroupIDs(MgmtIdImg)

    @staticmethod
    def setState(new_state, seq=0):
        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.IMAGE, MgmtIdImg.STATE, seq=seq)
        return CmdImg(hdr, new_state)

    @staticmethod
    def setStateCompleted(rsp):
        cmd = CmdImg.decode_header(rsp)

        # no complete packet
        if not cmd.hdr or not cmd.payload_bytes:
            if CmdBase._debug:
                print('decode common ret: ', str(cmd))
            return cmd

        if cmd.hdr.op != MgmtOp.WRITE_RSP or cmd.hdr.group != MgmtGroup.IMAGE or cmd.hdr.id != MgmtIdImg.STATE:
            raise ValueError('Unexpected response: {}'.format(cmd.hdr))

        dec_msg = cmd.decode()
        rc = 0
        if CmdBase._debug:
            print('decoded:', str(dec_msg))
        if 'rc' in dec_msg:
            raise ValueError('Missing return code in payload')
            rc = dec_msg['rc']


        if rc == 0:
            if CmdBase._debug:
                print(ImgDescription(dec_msg))
                for idx, sl in enumerate(ImgDescription(dec_msg).slots):
                    print('image:{} {}'.format(idx, str(sl)))
        else:
            err = MgmtErr(rc)
            raise ValueError('{}: {}'.format(err.value, str(err)))

        return cmd

    @staticmethod
    def getStateCompleted(rsp):
        cmd = CmdImg.decode_header(rsp)

        # no complete packet
        if not cmd.hdr or not cmd.payload_bytes:
            if CmdBase._debug:
                print('decode common ret: ', str(cmd))
            return cmd

        if cmd.hdr.op != MgmtOp.READ_RSP or cmd.hdr.group != MgmtGroup.IMAGE or cmd.hdr.id != MgmtIdImg.STATE:
            raise ValueError('Unexpected response: {}'.format(cmd.hdr))

        dec_msg = cmd.decode()
        if CmdBase._debug:
            print(dec_msg)
            print(ImgDescription(dec_msg))
            for idx, sl in enumerate(ImgDescription(dec_msg).slots):
                print('image:{} {}'.format(idx, str(sl)))

        return cmd


    @staticmethod
    def getState(seq=0):
        hdr = MgmtHeader(MgmtOp.READ, MgmtGroup.IMAGE, MgmtIdImg.STATE, seq=seq)
        return CmdImg(hdr, {})


    @staticmethod
    def imageConfirm(seq=0):

        return CmdImg.setState({
                    'confirm': True
                }, seq=seq)

    @staticmethod
    def imageUploadStart(img_bytes, offset, max_len, sha, seq=0):

        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.IMAGE, MgmtIdImg.UPLOAD, seq=seq)

        # Need to check how much data to append.
        cmd = CmdImg(hdr, {
                'off': offset,
                'len': len(img_bytes),
                'image': 0,
                'data': b'',
                'sha': sha
            })

        pkt_len = len(cmd.encode())
        if pkt_len >= max_len:
            # can we fragement it ? can we start w/o data attribute?
            raise ValueError('MTU to short for this packet')


        d_len = max_len - pkt_len
        if CmdBase._debug:
            print('Lengths: max:', max_len, 'pkt:', pkt_len, 'd:', d_len)
            print('dl:', len(img_bytes[offset:(offset + d_len)]))
            print('Adding', d_len, 'bytes of data')

        return CmdImg(hdr, {
                'off': offset,
                'sha': sha,
                'image': 0,
                'len': len(img_bytes),
                'data': img_bytes[offset:(offset + d_len)],
            })

    @staticmethod
    def imageUploadContinue(img_bytes, offset, max_len, seq=0, data_len_hint=0):

        # Done
        if offset >= len(img_bytes) or offset < 0:
            return None

        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.IMAGE, MgmtIdImg.UPLOAD, seq=seq)

        # Need to check how much data to append.
        cmd = CmdImg(hdr, {
                'off': offset,
                'image': 0,
                'data': b''
            })

        pkt_len = len(cmd.encode())
        if pkt_len >= max_len:
            # can we fragement it ? can we start w/o data attribute?
            raise ValueError('MTU to short for this packet')

        d_len = max_len - pkt_len
        if CmdBase._debug:
            print('offset', offset)
        return CmdImg(hdr, {
                    'off': offset,
                    'image': 0,
                    'data': img_bytes[offset:(offset + d_len)],
                })


    @staticmethod
    def imageErase(seq=0):
        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.IMAGE, MgmtIdImg.ERASE, seq=seq)
        return CmdImg(hdr, {})

    @staticmethod
    def imageEraseCompleted(rsp):
        cmd = CmdImg.decode_header(rsp)

        # no complete packet
        if not cmd.hdr or not cmd.payload_bytes:
            if CmdBase._debug:
                print('decode common ret: ', str(cmd))
            return cmd

        if cmd.hdr.op != MgmtOp.WRITE_RSP or cmd.hdr.group != MgmtGroup.IMAGE or cmd.hdr.id != MgmtIdImg.ERASE:
            raise ValueError('Unexpected response: {}'.format(cmd.hdr))

        dec_msg = cmd.decode()
        rc = 0
        if CmdBase._debug:
            print('decoded:', str(dec_msg))

        if not 'rc' in dec_msg:
            raise ValueError('Missing return code in payload')

        rc = dec_msg['rc']
        if rc != 0:
            err = MgmtErr(rc)
            raise ValueError('{}: {}'.format(err.value, str(err)))

        return cmd

class ImageErase(RequestBase):
    def __init__(self):
        super().__init__()

    def message(self):
        if self.response_data:
            return None

        return CmdImg.imageErase()

    def parse_response(self, rsp):
        rsp_cmd = CmdImg.imageEraseCompleted(rsp)
        self.response_data = rsp_cmd.payload_dict
        return self.response_data

class ImageList(RequestBase):
    def __init__(self):
        super().__init__()

    def message(self):
        if self.response_data:
            return None

        return CmdImg.getState()

    def parse_response(self, rsp):
        rsp_cmd = CmdImg.getStateCompleted(rsp)
        self.response_data = rsp_cmd.payload_dict
        return self.response_data

class ImageTest(RequestBase):
    def __init__(self, sha):
        super().__init__()
        if isinstance(sha, str):
            if len(sha) != 64:
                raise ValueError("Wrong hash length: {}".format(len(sha)))
            sha_b = bytes([ int(sha[idx:idx+2], 16) for idx in range(0, len(sha), 2) ])
        elif isinstance(sha, bytes):
            if len(sha) != 32:
                raise ValueError("Wrong hash length: {}".format(len(sha)))

            sha_b = sha
        assert type(sha_b) == bytes
        self.sha = sha
        self._sha_b = sha_b
        return


    def message(self):
        if self.response_data:
            return None

        return CmdImg.setState({
                    'confirm': False,
                    'hash': self._sha_b
                })

    def parse_response(self, rsp):
        rsp_cmd = CmdImg.setStateCompleted(rsp)
        self.response_data = rsp_cmd.payload_dict
        return self.response_data


class ImageConfirm(RequestBase):
    def __init__(self):
        super().__init__()

    def message(self):
        if self.response_data:
            return None

        return CmdImg.setState({
                    'confirm': True
                })

    def parse_response(self, rsp):
        rsp_cmd = CmdImg.setStateCompleted(rsp)
        self.response_data = rsp_cmd.payload_dict
        return self.response_data


class ImageUpload(RequestBase):
    def __init__(self, mcuboot_image, mtu=252, progress=False):
        super().__init__()
        self.image = mcuboot_image.data
        self.sha = mcuboot_image.hash()
        self.current_offset = 0
        self.next_offset = 0
        self.len = len(mcuboot_image.data)
        self.image_slot = 0
        # Need 12 b for other proto layers?
        self.mtu = mtu - 5
        self.seq = 0
        self.progress = progress

    def message(self):
        if self.response_data == None:
            cmd = CmdImg.imageUploadStart(self.image, self.current_offset, self.mtu, self.sha)
            self.next_offset = self.current_offset + len(cmd.payload_dict['data'])

        elif self.current_offset >= len(self.image):
            # we are done
            return None
        else:
            cmd =  CmdImg.imageUploadContinue(self.image, self.current_offset, self.mtu, self.sha)
            self.next_offset = self.current_offset + len(cmd.payload_dict['data'])

        return cmd


    def parse_response(self, rsp):
        hdr = MgmtHeader.decode(rsp)
        if hdr.op != MgmtOp.WRITE_RSP or hdr.group != MgmtGroup.IMAGE or hdr.id != MgmtIdImg.UPLOAD:
            raise ValueError('Unexpected response: {}'.format(hdr))

        if len(rsp) > hdr.size:
            dec_msg = CborAttr.decode(rsp[hdr.size:])[0]
            if CmdBase._debug:
                print(dec_msg)

        self.response_data = dec_msg

        if self.response_data['off'] != self.next_offset:
            print('Missed a packet, resending offset:', self.response_data['off'], file=sys.stderr)

        self.current_offset = self.response_data['off']

        if self.progress:
            percent = (self.current_offset / len(self.image)) * 100
            print('{} / {} ({:3.1f}%)'.format(self.current_offset, len(self.image)), percent)

        return self.response_data


def _image_hash(val):
    if isinstance(val, str):
        if len(val) != 64:
            raise ValueError("Wrong hash string length")

        return val

    raise ValueError("Wrong format: hash")


def registerImageCommandArguments(sub_parsers):
    img_cmd_parser = sub_parsers.add_parser('image', help='Manage images on a device')

    img_subs = img_cmd_parser.add_subparsers(title='Available Commands', dest='img_cmd')
    img_subs.add_parser('list', help='Show images on a device')
    img_subs.add_parser('confirm', help='Confirm active image')
    testparser = img_subs.add_parser('test', help='Test an image on next reboot')
    # testparser.add_argument('hash', type=str, required=True)
    testparser.add_argument('hash', type=_image_hash, default=None)

    uploadparser = img_subs.add_parser('upload', help='Upload image to a device')
    # uploadparser.add_argument('hash', type=str, required=True)
    uploadparser.add_argument('file', default=None)

    img_subs.add_parser('erase', help='Erase unused image on a device')

    return img_cmd_parser
'''
/*
 * Response to list:
 * {
 *      "images":[ <version1>, <version2>]
 * }
 *
 *
 * Request to boot to version:
 * {
 *      "test":<version>
 * }
 *
 *
 * Response to boot read:
 * {
 *	"test":<version>,
 *	"main":<version>,
 *      "active":<version>
 * }
 *
 *
 * Request to image upload:
 * {
 *      "off":<offset>,
 *      "len":<img_size>		inspected when off = 0
 *      "data":<base64encoded binary>
 * }
 *
 *
 * Response to upload:
 * {
 *      "off":<offset>
 * }
 *
 *
 * Request to image upload:
 * {
 *      "off":<offset>
 *	    "name":<filename>		inspected when off = 0
 *      "len":<file_size>		inspected when off = 0
 *      "data":<base64encoded binary>
 * }
'''