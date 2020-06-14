
from gi.repository import GLib


from pydbusbluez import Gatt, FormatRaw, GattService, GattCharacteristic, Adapter, BluezError
from .transport import CmdTimeout

import sys
import time

GATT_MCUMGR = [
    {
        'name': 'mcumgr_service',
        'uuid': '8D53DC1D-1DB7-4CD3-868B-8A527460AA84',
        'chars': [
            {
                'name': 'mcumgr_char',
                'uuid': 'da2e7828-fbce-4e01-ae9e-261174997c48',
                'fmt': FormatRaw
            }
        ] ,
    }
]

class GattCharacteristicMcumgr(GattCharacteristic):
    def __init__(self):
        super().__init__(
            GATT_MCUMGR[0]['chars'][0]['name'],
            GATT_MCUMGR[0]['chars'][0]['uuid'],
            GATT_MCUMGR[0]['chars'][0]['fmt']
        )

class GattServiceMcumgr(GattService):
    def __init__(self):
        self.mcumgr_char = GattCharacteristicMcumgr()
        self.mcumgr_char.service = self
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

        super().__init__(d, GATT_MCUMGR, warn_unmatched=False)


# TODO does this work as method?
def mcumgr_char_req(transport):
    next_msg = transport.request.message()

    if next_msg:
        transport.seq = (transport.seq + 1) % 256
        try:
            cmd_enc = next_msg.encode(transport.seq)
        except Exception as ex:
            transport.loop.quit()
            transport.response = ex

        # encode will set leng and seq, print afterwards
        if transport.debug:
            print(next_msg.hdr)
            print(next_msg.payload_dict)
        transport.timeout.start()
        try:
            transport.gatt.mcumgr_service.mcumgr_char.write(cmd_enc)
        except BluezError as e:
            transport.response = e
            transport.loop.quit()
    else:
        transport.loop.quit()

    return False

# TODO does this work as method?
def mcumgr_char_rsp(char, changed_vals, transport=None):
    try:
        if transport.debug:
            print(char, changed_vals)
            print(transport)

        transport.timeout.cancel()

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
            if transport.debug:
                print('Transport: Incomplete complete header')
            return
        if transport.debug:
            print(cmd_rsp.hdr)
        if (cmd_rsp.hdr.size + cmd_rsp.hdr.length) > len(transport.fragment):
            if transport.debug:
                print('Transport: Fragmented packet')
            return

        pkt_data = transport.fragment
        pkt_seq = transport.seq
        transport.fragment = None

        # check duplicates
        if pkt_seq > cmd_rsp.hdr.seq:
            #ignore for now, this resonse already timed out and we made a new request.
            print('Transport: Got duplicate: ', str(cmd_rsp.hdr), "expected seq:", pkt_seq, file=sys.stderr)
            return
        elif pkt_seq < cmd_rsp.hdr.seq:
            #ignore for now, this resonse already timed out and we made a new request.
            print('Transport: Got duplicate: ', str(cmd_rsp.hdr), "expected seq:", pkt_seq, file=sys.stderr)
            return

        transport.response = transport.request.parse_response(pkt_data)

        # got packet:
        if transport.debug:
            print('Transport: Received:', transport.response)

        if transport.response.err:
            print(transport.response.err, file=sys.stderr)
            transport.loop.quit()
        if transport.debug:
            print(transport.response.obj)

        mcumgr_char_req(transport)


    # catch all and save object for reraising from main context
    except Exception as e:
        transport.response = e
        transport.loop.quit()


class TransportBLE(object):

    _valid_cs_attrs = ['peer_id']

    def __init__(self, timeout=10, adapter=0, peer_id=None, peer_name=None):
        self.peer_id = peer_id.upper()
        self.peer_name = peer_name
        self.loop = GLib.MainLoop()
        self.cmd_timeout = timeout
        self.timeout = CmdTimeout(self.cmd_timeout, self.loop.quit)
        self.adapter = adapter if str(adapter).startswith('hci') else 'hci' + str(adapter)
        self.gatt = None
        self.fragment = None
        self.seq = -1
        self.response_decode_cb = None
        self.response = None
        self.debug = False
        self.scan_args = None

    def set_timeout(self, timeout_sec):
        self.cmd_timeout = timeout_sec
        if self.timeout:
            self.timeout.cancel()
            self.timeout.timeout = self.cmd_timeout


    def run(self, request):
        self.request = request

        if not (self.gatt and
                self.gatt.dev and
                self.gatt.dev.connected and
                self.gatt.mcumgr_service.mcumgr_char.obj):
            self._connect()

        mcumgr_char = self.gatt.mcumgr_service.mcumgr_char
        if not mcumgr_char.obj:
            print('Device {} does not support mcumgr characteristic'.format(self.peer_id), file=sys.stderr)
            sys.exit(1)
        elif self.debug:
            print('Found mcumgr characteristic at', mcumgr_char.obj)

        mcumgr_char.onValueChanged(mcumgr_char_rsp, transport=self)
        mcumgr_char.notifyOn()


        GLib.timeout_add_seconds(0, mcumgr_char_req, self)
        try:
            self.loop.run()
            self.timeout.cancel()
        except (SystemExit, KeyboardInterrupt) as e:
            self.timeout.cancel()
            raise e from None

        try:
            mcumgr_char.onValueChanged(None)
            mcumgr_char.notifyOff()
        except (BluezError, GLib.Error):
            pass

        # if self.response:
        #     return self.response.payload_dict

        if self.timeout.remaining <= 0:
            print('NMP Timeout:', str(request), file=sys.stderr)
            return None

        # raise / return Error, maybe not the best, but will do for now
        if self.response and isinstance(self.response, Exception):
            #raise self.response # pylint: disable=raising-bad-type,
            print('Error:', str(self.response), file=sys.stderr)
            return None

        return self.response


    def _connect(self):
        try:
            hci = Adapter(self.adapter)
        except BluezError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        dev = None
        try:
            devs = hci.devices()
            for d in devs:
                if self.debug:
                    print('Transport: Found device:', str(d))
                if d.name.upper() == self.peer_id.upper():
                    dev = d
                    break

        except BluezError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        if not dev:
            if self.debug:
                print('Transport: Scanning on {} ..'.format(hci.name))
            hci.scan(filters=self.scan_args)
            # TODO: make this async
            to = self.timeout.timeout
            while to >= 0 and not dev:
                to -= 2
                time.sleep(2)

                try:
                    devs = hci.devices()
                    for d in devs:
                        if d.name.upper() == self.peer_id.upper():
                            dev = d
                            break

                except BluezError as e:
                    print(str(e), file=sys.stderr)
                    sys.exit(1)
            try:
                hci.scan(enable=False)
            except BluezError as e:
                print(str(e), file=sys.stderr)

        if not dev:
            if self.peer_id:
                print('Transport: device {} not found nearby'.format(self.peer_id))
            else:
                print('Transport: device not found nearby')

            sys.exit(1)

        try:
            dev.connect()
        except BluezError as e:
            print(str(e))
            sys.exit(1)

        if self.debug:
            print('Transport: Connected')

        mcumgr = GattMcumgr(d)
        mcumgr_char = mcumgr.mcumgr_service.mcumgr_char

        self.gatt = mcumgr


    def close(self):
        try:
            self.gatt.mcumgr_service.mcumgr_char.notifyOff()
        except BluezError:
            pass
        try:
            self.gatt.dev.disconnect()
        except BluezError:
            pass

        self.gatt = None
        if self.timeout:
            self.timeout.cancel()


    @staticmethod
    def fromCmdArgs(args):
        connstring = args.connstring
        if not connstring:
            raise ValueError('Missing --connstring option')
        cs_attr_l = connstring.split(',')
        for cs_attr in cs_attr_l:
            cs_attrs = cs_attr.split('=')
            if not len(cs_attrs) == 2:
                raise ValueError('--connstring attributes must be key=value, e.g. --connstring "peer_id=aa:bb:cc:dd:ee:ff"')

            n_connstring = {}
            if not cs_attrs[0] in TransportBLE._valid_cs_attrs:
                raise ValueError(
                    'Unknown connstring key \'{}\' for \'ble\', must be one of {}'.format(
                        cs_attrs[0], TransportBLE._valid_cs_attrs)
                )
            n_connstring[cs_attrs[0]] = cs_attrs[1]

        if args.hci:
            n_connstring['adapter'] = args.hci

        return TransportBLE(**n_connstring)

    def __str__(self):
        return 'conntype=ble,peer_id={}'.format(self.peer_id)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, str(self))
