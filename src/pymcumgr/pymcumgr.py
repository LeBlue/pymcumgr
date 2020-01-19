#!/usr/bin/env python3

import sys
import time
from pymcumgr.mgmt.os_cmd import registerOSCommandArguments, Reset, Echo
from pymcumgr.mgmt.img_cmd import ImgDescription, registerImageCommandArguments, ImageList, ImageConfirm, ImageTest, ImageErase, ImageUpload
from pymcumgr.mgmt.header import MgmtHeader, MgmtOp, MgmtGroup, MgmtErr
from pymcumgr.mgmt.mcuboot_image import MCUBootImage, print_hex as print_hex2

from pymcumgr.transport.ble_transport import TransportBLE



from argparse import ArgumentParser

_usage='''
  %(prog)s [options]'''



def cmd_finished(transport, err, response):
    print(transport)
    if err:
        print('err:', str(err))
    else:
        print(response)
    transport.close()

def parse_connstring(args):
    try:
        ct = args.conntype
    except AttributeError:
        ct = 'ble'

    if ct == 'ble':
        if not args.connstring:
            return args

        args.connstring = TransportBLE.fromCmdArgs(args)
    else:
        raise ValueError('Supported conntypes: [\'ble\']')

    return args






def main():

    parser = ArgumentParser(
        description='%(prog)s helps you manage remote devices',
        usage=_usage,
        epilog='Use "%(prog)s [command] --help" for more information about a command.'
    )

    # parser.add_argument('cmd', default=None)
    parser.add_argument('--connstring', metavar='string', type=str, default=None,
                        help='Connection key-value pairs to use instead of using the profile\'s connstring'
    )
    #only ble for now, set as default
    parser.add_argument('--conntype', metavar='string', type=str, default='ble',
                        help='Connection type to use instead of using the profile\'s type'
    )
    parser.add_argument('-i', '--hci', metavar='int', type=int, default=0,
                        help='HCI index for the controller on Linux machine'
    )
    parser.add_argument('-t', '--timeout', metavar='float', type=float, default=10,
                        help='timeout in seconds (partial seconds allowed) (default 10)'
    )

    # sub command parser
    subs = parser.add_subparsers(title='Available Commands',
                                description=None,
                                dest='command')

    #
    registerImageCommandArguments(subs)
    registerOSCommandArguments(subs)


    args = parser.parse_args()

    print(args)
    # args = parse_connstring(args)
    print(args)

    #sys.exit(1)

    # loop = GLib.MainLoop()
    # timeout = CmdTimeout(args.timeout, loop)

    # handle static commmands here
    if args.command == 'image':
        if args.img_cmd == 'analyze':
            with open(args.file, 'rb') as f:
                contents = f.read()

            img = MCUBootImage(contents)
            print(img)
            sys.exit(0)



    # class BTCommand(object):
    #     def __init__(self, run, args=None):
    #         self.run = run
    #         self.args = args
    #         self.ret = 0
    #         self.timestamp = 0

    #     def send(self):
    #         pass


    # command_list = [
    #     (send_echo, 'OK'),
    #     (send_image_list, ''),
    #     (send_image_test, '')
    # ]

    #GLib.timeout_add_seconds(args.timeout, quit_loop, loop)
    transport = TransportBLE.fromCmdArgs(args)

    if args.command == 'image':
        if args.img_cmd == 'list':
            # GLib.timeout_add_seconds(0, send_image_list, mcumgr_char, None, loop)
            rsp = transport.run(ImageList())
            #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))
        elif args.img_cmd == 'confirm':
            rsp = transport.run(ImageConfirm())
            #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))
            # GLib.timeout_add_seconds(0, send_image_confirm, mcumgr_char, None, loop)
        elif args.img_cmd == 'test':
            rsp = transport.run(ImageTest(args.hash))
            #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))

            # GLib.timeout_add_seconds(0, send_image_test, mcumgr_char, img_hash, loop)
        elif args.img_cmd == 'upload':
            #img_hash = 'b47ab3d5617e38ba978bd7ef0a56adf7ea340000611fe7223327c4849cd0a848'

            with open(args.file, 'rb') as f:
                contents = f.read()

            # upload_handler = UploadHandler(MCUBootImage(contents), mtu=252)
            rsp = transport.run(ImageUpload(MCUBootImage(contents), mtu=252))
            #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
            print('upload returend')
            print(rsp)
            if rsp:
                print('Done')
        elif args.img_cmd == 'erase':
            rsp = transport.run(ImageErase())
            #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
            print('erase returend')
            if rsp:
                print(rsp)
            print('Done')


        else:
            raise NotImplementedError('Image command: {}'.format(args.img_cmd))

    elif args.command == 'echo':
        rsp = transport.run(Echo(args.text))
        #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
        print('echo returend')
        if rsp:
            print(rsp)
        print('Done')

    elif args.command == 'reset':
        rsp = transport.run(Reset())
        #GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)
        print('reset returend')
        if rsp:
            print(rsp)
        print('Done')

    else:
        raise NotImplementedError('Command: {}'.format(args.command))


    #sys.exit(1)

    # try:
    #     loop.run()
    # except (SystemExit, KeyboardInterrupt):
    #     pass

def image_list():
    GLib.timeout_add_seconds(0, send_command, mcumgr_char, loop, timeout, CmdImg.imageList)

def image_confirm():
    pass


if __name__ == "__main__":
    main()