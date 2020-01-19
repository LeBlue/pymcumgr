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
    subs.add_parser('version', help='Display the %(prog)s version number')

    args = parser.parse_args()

    #print(args)

    # handle static commmands here
    if args.command == 'version':
        from pymcumgr import __version__
        print(__version__)
        sys.exit(0)
    elif args.command == 'image':
        if args.img_cmd == 'analyze':
            with open(args.file, 'rb') as f:
                contents = f.read()

            img = MCUBootImage(contents)
            print(img)
            sys.exit(0)


    transport = TransportBLE.fromCmdArgs(args)

    if args.command == 'image':
        if args.img_cmd == 'list':

            rsp = transport.run(ImageList())

            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))
        elif args.img_cmd == 'confirm':
            rsp = transport.run(ImageConfirm())

            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))

        elif args.img_cmd == 'test':
            rsp = transport.run(ImageTest(args.hash))

            print('list returend')
            print(rsp)
            if rsp:
                for idx, sl in enumerate(ImgDescription(rsp).slots):
                    print('image:{} {}'.format(idx, str(sl)))


        elif args.img_cmd == 'upload':

            with open(args.file, 'rb') as f:
                contents = f.read()

            # TODO: don't know how to obtain MTU, set static for now
            rsp = transport.run(ImageUpload(MCUBootImage(contents), mtu=252))

            print('upload returend')
            print(rsp)
            if rsp:
                print('Done')
        elif args.img_cmd == 'erase':
            rsp = transport.run(ImageErase())

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