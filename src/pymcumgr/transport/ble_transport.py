
from gi.repository import GLib


from pydbusbluez import Gatt, FormatRaw, GattService, GattCharacteristic, Adapter, BluezError
from .transport import CmdTimeout

import sys
import time

GATT_MCUMGR = [
    {
        "name": "mcumgr_service",
        "uuid": "8D53DC1D-1DB7-4CD3-868B-8A527460AA84",
        "chars": [
            {
                "name": "mcumgr_char",
                "uuid": "da2e7828-fbce-4e01-ae9e-261174997c48",
                "form": FormatRaw
            }
        ] ,
    }
]

class GattCharacteristicMcumgr(GattCharacteristic):
    def __init__(self):
        super().__init__(
            GATT_MCUMGR[0]['chars'][0]['name'],
            GATT_MCUMGR[0]['chars'][0]['uuid'],
            GATT_MCUMGR[0]['chars'][0]['form']
        )

class GattServiceMcumgr(GattService):
    def __init__(self):
        self.mcumgr_char = GattCharacteristicMcumgr()
        self.chars = [self.mcumgr_char]
        super().__init__(
            GATT_MCUMGR[0]['name'],
            GATT_MCUMGR[0]['uuid']
        )

class GattMcumgr(Gatt):
    def __init__(self, d):

        m_serv = GattServiceMcumgr()
        self.mcumgr_service = m_serv
        self.services = [self.mcumgr_service]

        super().__init__(d, GATT_MCUMGR)




# TODO does this work as method?
def mcumgr_char_rsp(char, changed_vals, transport=None):
    try:
        print(char, changed_vals)
        print(transport)
        # msg = changed_vals.value
        #err = 1
    #    last_fragm = transport.fragment
        transport.timeout.reset()

        if transport.fragment:
            transport.fragment = transport.fragment + changed_vals.value
        else:
            transport.fragment = changed_vals.value

        # better decode header first, check seq
        # try:
        cmd_rsp = transport.request.response_header(transport.fragment)
        # except ValueError as e:
            # print('Response decode error:', str(e))
            # transport.loop.quit()
            # return

        # wait for more
        if not cmd_rsp.hdr:
            print("No compleete hdr")
            return
        print(cmd_rsp.hdr)
        if (cmd_rsp.hdr.size + cmd_rsp.hdr.length) > len(transport.fragment):
            print('Fragmented packet')
            return

        pkt_data = transport.fragment
        pkt_seq = transport.seq
        transport.seq = (transport.seq + 1) % 256
        transport.fragment = None

        # check duplicates
        if pkt_seq > cmd_rsp.hdr.seq:
            #ignore for now, this resonse already timed out and we made a new request.
            print('Got duplicate: ', str(cmd_rsp.hdr))
            return

        transport.response = transport.request.parse_response(pkt_data)

        # got packet:
        print('Received:', transport.response)

        next_msg = transport.request.message()
        if next_msg:

            cmd_enc = next_msg.encode(transport.seq)
            transport.timeout.reset()
            transport.gatt.mcumgr_service.mcumgr_char.write(cmd_enc)
        else:
            transport.loop.quit()
    except Exception as e:
        transport.response = e
        transport.loop.quit()


class TransportBLE(object):

    _valid_cs_attrs = ['peer_id']

    def __init__(self, timeout=10, adapter=0, peer_id=None, peer_name=None):
        self.peer_id = peer_id.upper()
        self.peer_name = peer_name
        self.loop = GLib.MainLoop()
        self.timeout = CmdTimeout(timeout, self.loop)
        self.adapter = 'hci' + str(adapter)
        self.gatt = None
        self.fragment = None
        self.seq = 0
        self.response_decode_cb = None
        self.response = None

    def run(self, request):
        # self.response_decode_cb = response_decode_cb
        self.request = request

        if not self.gatt or not self.gatt.dev or not self.gatt.dev.connected():
            self._connect()


        self.seq += 1
        cmd_enc = request.message().encode(self.seq)
        GLib.timeout_add_seconds(0, self.gatt.mcumgr_service.mcumgr_char.write, cmd_enc)

        try:
            self.loop.run()
        except (SystemExit, KeyboardInterrupt) as e:
            raise e from None

        # if self.response:
        #     return self.response.payload_dict

        # raise / return Error, maybe not the best, but will do for now
        if self.response and isinstance(self.response, Exception):
            raise self.response # pylint: disable=raising-bad-type,

        return self.response


    def _connect(self):
        try:
            hci = Adapter(self.adapter)
        except BluezError as e:
            print(str(e))
            sys.exit(1)

        dev = None
        try:
            devs = hci.devices()
            for d in devs:
                print(str(d))
                if d.name.upper() == self.peer_id.upper():
                    dev = d
                    break

        except BluezError as e:
            print(str(e))
            sys.exit(1)

        if not dev:
            print('scanning')
            hci.scan()
            time.sleep(3)
            hci.scan(enable=False)

            try:
                devs = hci.devices()
                for d in devs:
                    if d.name.upper() == self.peer_id.upper():
                        dev = d
                        break

            except BluezError as e:
                print(str(e))
                sys.exit(1)

        if not dev:
            print("dev not found nearby")
            sys.exit(1)

        try:
            dev.connect()
        except BluezError as e:
            print(str(e))
            sys.exit(1)

        print('connected')

        mcumgr = GattMcumgr(d)
        mcumgr_char = mcumgr.mcumgr_service.mcumgr_char


        mcumgr_char.notifyOn(mcumgr_char_rsp, transport=self)

        self.gatt = mcumgr

    @staticmethod
    def fromCmdArgs(args):
        connstring = args.connstring
        cs_attr_l = connstring.split(',')
        for cs_attr in cs_attr_l:
            cs_attrs = cs_attr.split('=')
            if not len(cs_attrs) == 2:
                raise ValueError('Connstring attributes must be key=value')

            n_connstring = {}
            if not cs_attrs[0] in TransportBLE._valid_cs_attrs:
                raise ValueError(
                    'Unknown connstring key \'{}\' for \'ble\', must be one of {}'.format(
                        cs_attrs[0], TransportBLE._valid_cs_attrs)
                )
            n_connstring[cs_attrs[0]] = cs_attrs[1]

        return TransportBLE(**n_connstring)

    def __str__(self):
        return 'peer_id={}'.format(self.peer_id)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, str(self))