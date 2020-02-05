from gi.repository import GLib
import sys

class CmdTimeout(object):

    def __init__(self, timeout_secs, loop, expired_cb=None, *args, **kwargs):
        self.timeout = timeout_secs
        self.remaining = timeout_secs
        self.canceled = False
        if expired_cb:
            self.expired_cb = expired_cb
            self.expired_cb_args = args
            self.expired_cb_kwargs = kwargs
        else:
            def mainloop_quit():
                print('NMP Timeout', file=sys.stderr)
                loop.quit()

            self.expired_cb = mainloop_quit
            self.expired_cb_args = ()
            self.expired_cb_kwargs = {}
        #GLib.timeout_add_seconds(1, self._tick)


    def _tick(self):
        self.remaining -= 1
        if self.remaining <= 0 and not self.canceled:
            if self.expired_cb:
                self.expired_cb(*self.expired_cb_args, **self.expired_cb_kwargs)
            return False

        return not self.canceled

    def reset(self):
        self.remaining = self.timeout

    def start(self):
        self.reset()
        self.canceled = False
        GLib.timeout_add_seconds(1, self._tick)

    def cancel(self):
        self.canceled = True


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


