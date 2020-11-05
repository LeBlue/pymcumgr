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

    _registered = {}

    @classmethod
    def fromCmdArgs(cls, args):
        if not args.conntype or not args.conntype in cls._registered:
            raise ValueError(
                'Missing or unknown conntype, supported: {}'.format(
                    list(cls._registered))
                )

        return cls._registered[args.conntype].fromCmdArgs(args)


    @classmethod
    def register(cls, trsp):
        cls._registered[trsp.conntype()] = trsp

    @classmethod
    def transport_types(cls):
        return list(cls._registered)
