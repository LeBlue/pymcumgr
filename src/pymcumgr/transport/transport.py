from gi.repository import GLib
import sys

class CmdTimeout(object):

    def __init__(self, timeout_secs, cb, *args, **kwargs):
        self.timeout = timeout_secs
        self.remaining = timeout_secs
        self.canceled = False
        self.expired_cb = cb
        self.expired_cb_args = args
        self.expired_cb_kwargs = kwargs
        self._event_id = None


    def _expired(self):
        self.remaining = 0
        self._event_id = None
        if self.expired_cb:
            self.expired_cb(*self.expired_cb_args, **self.expired_cb_kwargs)
        return False

    def reset(self):
        self.cancel()
        self.start()

    def start(self):
        self.remaining = self.timeout
        self._event_id = GLib.timeout_add_seconds(self.timeout, self._expired)

    def cancel(self):
        if self._event_id != None:
            GLib.source_remove(self._event_id)
            self._event_id = None


class Transport(object):

    _valid_transports = ['ble']

    @staticmethod
    def fromCmdArgs(args):
        if not args.conntype or not args.conntype in Transport._valid_transports:
            raise ValueError(
                'Missing or unknown conntype, supported: {}'.format(
                    Transport._valid_transports)
                )
        if args.conntype == 'ble':
            return TransportBLE.fromCmdArgs(args)


