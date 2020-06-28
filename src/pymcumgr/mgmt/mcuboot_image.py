
from collections import namedtuple
import struct

# Field names for mcuboot header, with struct image_version inlined,
# as well as struct module format string and reprs format strings for
# each.
IMG_HDR_FIELDS = [
    'magic', 'load_addr', 'hdr_size', 'img_size', 'flags',
    'ver_major', 'ver_minor', 'ver_revision', 'ver_build_num']
IMG_HDR_FMT = '<IIHxxIIbbhIxxxx'
IMG_HDR_MAGIC = 0x96f3b83d

IMAGE_F_RAM_LOAD = 0x00000020

TLV_INFO_FIELDS = ['magic', 'tlv_size']
TLV_INFO_FMT = '<HH'
TLV_INFO_SIZE = 4
TLV_INFO_MAGIC = 0x6907

TLV_HDR_FIELDS = ['type', 'len']
TLV_HDR_FMT = '<bxH'
TLV_HDR_SIZE = 4
TLV_HDR_TYPES = {
    0x01: 'IMAGE_TLV_KEYHASH',
    0x10: 'IMAGE_TLV_SHA256',
    0x20: 'IMAGE_TLV_RSA2048_PSS',
    0x21: 'IMAGE_TLV_ECDSA224',
    0x22: 'IMAGE_TLV_ECDSA256'
    }


class ImageHeader(namedtuple('ImageHeader', IMG_HDR_FIELDS)):

    def __repr__(self):
        return ('ImageHeader(magic={}/0x{:08X}, load_addr={}/0x{:08X}, '
                'hdr_size=0x{:04X}, img_size={}/0x{:08X}, flags=0x{:08X}, '
                'version="{}.{}.{}-build{}")').format(
                    'OK' if self._magic_ok() else 'BAD', self.magic,
                    'VALID' if self._load_addr_valid() else 'IGNORED',
                    self.load_addr,
                    self.hdr_size, self.img_size, self.img_size, self.flags,
                    self.ver_major, self.ver_minor, self.ver_revision,
                    self.ver_build_num)

    def _magic_ok(self):
        return self.magic == IMG_HDR_MAGIC

    def _load_addr_valid(self):
        return bool(self.flags & IMAGE_F_RAM_LOAD)

    def version(self):
        return '{}.{}.{}'.format(self.ver_major, self.ver_minor, self.ver_revision)




class TLVInfo(namedtuple('TLVInfo', TLV_INFO_FIELDS)):

    def __repr__(self):
        return 'TLVInfo(magic={}/0x{:04X}, tlv_size={})'.format(
            'OK' if self._magic_ok() else 'BAD', self.magic, self.tlv_size)

    def _magic_ok(self):
        return self.magic == TLV_INFO_MAGIC


class TLVHeader(namedtuple('TLVHeader', TLV_HDR_FIELDS)):

    def __repr__(self):
        return 'TLVHeader(type={}/0x{:02X}, len={})'.format(
            TLV_HDR_TYPES[self.type], self.type, self.len)


class MCUBootImage(object):
    def __init__(self, img_bytes):
        self.data = img_bytes
        self.header = ImageHeader(*struct.unpack_from(IMG_HDR_FMT, img_bytes))

        tlv_info_offset = self.header.hdr_size + self.header.img_size
        self.tlv_info = TLVInfo(*struct.unpack_from(TLV_INFO_FMT, img_bytes,
                                            offset=tlv_info_offset))

        tlv_end = tlv_info_offset + self.tlv_info.tlv_size
        tlv_off = tlv_info_offset + TLV_INFO_SIZE
        tlv_num = 0

        self.tlv_hdrs = []

        while tlv_off < tlv_end:
            tlv_hdr = TLVHeader(*struct.unpack_from(TLV_HDR_FMT, img_bytes,
                                                    offset=tlv_off))

            tlv_hdr_bytes = b''
            if tlv_hdr.len <= 32:
                start = tlv_off + TLV_HDR_SIZE
                end = start + tlv_hdr.len
                tlv_hdr_bytes = img_bytes[start:end]

            tlv_off += TLV_HDR_SIZE + tlv_hdr.len
            tlv_num += 1

            self.tlv_hdrs.append((tlv_hdr, tlv_hdr_bytes))

    @property
    def version(self):
        return self.header.version()


    def hash_str(self):
        return ''.join('{:02x}'.format(b) for b in self.hash())

    def hash(self):
        b = b''
        for tlv_hdr in self.tlv_hdrs:
            if tlv_hdr[0].type == 0x10:
                b = tlv_hdr[1]
                break

        return b


    def getHeaderBytes(self):
        start = self.header.hdr_size
        end = start + min(20, self.header.img_size)

        return self.data[start:end]


def print_hex(bs):
    print(' '.join('{:02x}'.format(b) for b in bs))



import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    args = parser.parse_args()

    with open(args.image, 'rb') as f:
        contents = f.read()


    mcuboot_img = MCUBootImage(contents)

    print(mcuboot_img.header)
    print_hex(mcuboot_img.getHeaderBytes())

    print(mcuboot_img.tlv_info)

    for tlv_num, tlv_hdr in enumerate(mcuboot_img.tlv_hdrs):
        print('TLV {}:'.format(tlv_num), tlv_hdr[0])
        print_hex(tlv_hdr[1])


    print('version:{} hash:{}'.format(mcuboot_img.version, mcuboot_img.hash_str()))


if __name__ == '__main__':
    main()
