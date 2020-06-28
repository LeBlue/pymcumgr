from enum import Enum
from .header import MgmtHeader, MgmtGroup, MgmtOp, MgmtErr, CmdBase, RequestBase, ResponseBase
from .cborattr import CborAttr

import time
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
            raise KeyError('key expected in slot: {}'.format(str(e))) from None

    def hash_str(self):
        return self.hash

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
        if CmdBase._debug:
            print(str(hdr))
            print(str(new_state))
        return CmdImg(hdr, new_state)

    @staticmethod
    def setStateCompleted(rsp, allow_missing_rc=False):
        cmd = CmdImg.decode_header(rsp)

        # no complete packet
        if not cmd.hdr or not cmd.payload_bytes:
            if CmdBase._debug:
                print('decode common ret: ', str(cmd))
            return cmd

        if cmd.hdr.op != MgmtOp.WRITE_RSP or cmd.hdr.group != MgmtGroup.IMAGE or cmd.hdr.id != MgmtIdImg.STATE:
            raise ValueError('Unexpected response: {}'.format(cmd.hdr))

        dec_msg = cmd.decode()
        if CmdBase._debug:
            print('decoded:', str(dec_msg))

        err = MgmtErr.from_response(dec_msg, allow_missing=allow_missing_rc)

        if not err:
            img_desc = ImgDescription(dec_msg)
            if CmdBase._debug:
                print(img_desc)
                for idx, sl in enumerate(img_desc.slots):
                    print('image:{} {}'.format(idx, str(sl)))

        else:
            raise ValueError('{}: {}'.format(err.value, str(err)))

        return ResponseBase(err, dec_msg, img_desc)

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

        err = MgmtErr.from_response(dec_msg, allow_missing=True)

        if not err:
            img_desc = ImgDescription(dec_msg)
            if CmdBase._debug:
                print(img_desc)
                for idx, sl in enumerate(img_desc.slots):
                    print('image:{} {}'.format(idx, str(sl)))

        else:
            raise ValueError('{}: {}'.format(err.value, str(err)))

        return ResponseBase(err, dec_msg, img_desc)


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
                'data': b'',
                'sha': sha
            })

        pkt_len = len(cmd.encode())
        if pkt_len >= max_len:
            # can we fragement it ? can we start w/o data attribute?
            raise ValueError('MTU to short for this packet')


        d_len = max_len - pkt_len
        if CmdBase._debug:
            print('Lengths: max_len:', max_len, 'pkt_len:', pkt_len, 'data_len:', d_len)
            print('data_len:', len(img_bytes[offset:(offset + d_len)]))
            print('Adding', d_len, 'bytes of data')

        # putting 'data' at end will trigger corruption in cbor on the FW. ( on z2.0.0)
        # ('data' key pointer will LSB will be set to 0, while copying sha value)
        # new accepted 'data' key will be some arbitrary string at that location
        return CmdImg(hdr, {
                'off': offset,
                'data': img_bytes[offset:(offset + d_len)],
                'sha': sha,
                'len': len(img_bytes),
            })

    @staticmethod
    def imageUploadContinue(img_bytes, offset, max_len, seq=0, data_len_hint=0):

        # Done
        if offset >= len(img_bytes) or offset < 0:
            return None

        hdr = MgmtHeader(MgmtOp.WRITE, MgmtGroup.IMAGE, MgmtIdImg.UPLOAD, seq=seq)

        # TODO: size hint does not work as encoded offset len increases (1byte/2byte/4byte..)
        # allocate 4 bytes for it, should not need more
        if not data_len_hint:
            # Need to check how much data to append.
            cmd = CmdImg(hdr, {
                    'off': 65536,
                    'data': b''
                })

            pkt_len = len(cmd.encode())

            if pkt_len >= max_len:
                # can we fragement it ? can we start w/o data attribute?
                raise ValueError('MTU to short for this packet')

            d_len = max_len - pkt_len
        else:
            d_len = data_len_hint

        if CmdBase._debug:
            print('UL Continue at offset', offset)

        if d_len <= 0:
            raise ValueError('Data len calculation failed, got:', d_len)

        return CmdImg(hdr, {
                    'off': offset,
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
        if CmdBase._debug:
            print('decoded:', str(dec_msg))

        err = MgmtErr.from_response(dec_msg)

        return ResponseBase(err, dec_msg, None)

class ImageErase(RequestBase):
    def __init__(self):
        super().__init__()

    def message(self):
        if self.response_data:
            return None

        return CmdImg.imageErase()

    def parse_response(self, rsp):
        rsp_cmd = CmdImg.imageEraseCompleted(rsp)
        self.response_data = rsp_cmd
        return self.response_data

class ImageList(RequestBase):
    def __init__(self):
        super().__init__()

    def message(self):
        if self.response_data:
            return None

        return CmdImg.getState()

    def parse_response(self, rsp):
        self.response_data = CmdImg.getStateCompleted(rsp)
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


    def message(self):
        if self.response_data:
            return None

        return CmdImg.setState({
                    'confirm': False,
                    'hash': self._sha_b
                })

    def parse_response(self, rsp):
        self.response_data = CmdImg.setStateCompleted(rsp, allow_missing_rc=True)
        return self.response_data

    def __str__(self):
        return '{}(hash={})'.format(self.__class__.__name__, self.sha)

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
        self.response_data = CmdImg.setStateCompleted(rsp, allow_missing_rc=True)
        return self.response_data


class ImageUpload(RequestBase):
    def __init__(self, mcuboot_image, mtu=252, progress=False):
        super().__init__()
        self.image = mcuboot_image
        self.sha = mcuboot_image.hash()
        self.current_offset = 0
        self.next_offset = 0
        self.retry_offset = 3
        self.len = len(mcuboot_image.data)
        self.image_slot = 0
        # Need 12 b for other proto layers?
        self.mtu = mtu - 5
        self.data_len_hint = 0
        self.seq = 0
        self.progress = progress
        self._progress_last = 0
        self._progress_init_offset = 0
        self.starttime = None

    def message(self):
        # Nothing received => starting message
        if self.response_data == None:
            self.starttime = time.time()
            cmd = CmdImg.imageUploadStart(self.image.data, self.current_offset, self.mtu, self.sha)
            self.next_offset = self.current_offset + len(cmd.payload_dict['data'])

        elif self.response_data.err:
            # last rsp was mgmt err
            return None
        elif self.current_offset >= len(self.image.data):
            # we are done
            if self.progress:
                et = time.time()
                elapsed = (et - self.starttime)
                speed = (self.len - self._progress_init_offset) / elapsed
                print('{} / {} (100%)'.format(len(self.image.data), len(self.image.data)))
                print('{}s ({:3.1f} kb/s)'.format(int(elapsed), speed/1024))
            return None

        # should not completely restart (in case MTU is to small to include first data)
        # newer mcumgr version will not even accept it
        else:
            cmd = CmdImg.imageUploadContinue(self.image.data, self.current_offset, self.mtu, data_len_hint=self.data_len_hint)
            self.data_len_hint = len(cmd.payload_dict['data'])
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
        else:
            # transport should handle this case
            raise ValueError('Complete header w/o payload: {}'.format(hdr))

        err = MgmtErr.from_response(dec_msg)
        if err:
            self.response_data = ResponseBase(err, dec_msg, None)
            return self.response_data

        if not 'off' in dec_msg:
            raise ValueError('Missing key \'off\' in response')

        if dec_msg['off'] != self.next_offset:
            if dec_msg['off'] < self.next_offset:
                if self.retry_offset >= 0:
                    print('Missed a packet, resending offset:', dec_msg['off'], file=sys.stderr)
                    self.retry_offset -= 1
                else:
                    raise ValueError("Exeeded retries on resend, off:", dec_msg['off'])
            else:
                print('Upload continue ...')
                self._progress_init_offset = dec_msg['off']
        else:
            self.retry_offset = 3

        self.current_offset = dec_msg['off']

        if self.progress:
            percent = int((self.current_offset / len(self.image.data)) * 100)
            # prevent exessive printing
            if percent - self._progress_last >= 1:
                self._progress_last = percent
                print('{} / {} ({}%)'.format(self.current_offset, len(self.image.data), percent))

        self.response_data = ResponseBase(err, dec_msg, None)
        return self.response_data

    def __str__(self):
        return '{}(image=MCUBootImage(version={},hash={}))'.format(self.__class__.__name__, self.image.version, self.image.hash_str())

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

