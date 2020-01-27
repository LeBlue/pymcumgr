
from tinycbor import CborEncoder, CborDecoder, CborType, CborError

def get_hex_str(b, width=32):
    h_b_l = []
    print(b)
    h_b = b.hex()
    print(h_b)

    lascii = list(map(lambda x: x if x.isprintable() and x !='�' else '.', b.decode('ascii', errors='replace')))
    lines = []
    for idx in range(0, len(b), width):
        h_b_l = []
        addr = '{:08x}'.format(idx)
        for id in range(idx, idx+width, 2):
            h_b_l.append(h_b[id:id+2])
        l = ' '.join(h_b_l)

        lines.append('{}: {}    |{}|'.format(addr, l, ''.join(lascii[idx:idx+width])))

    return '\n'.join(lines)

def print_hex(b, width=16):
    h_b_l = []
    h_b = b.hex()
    lascii = list(map(lambda x: x if x.isprintable() and x !='�' else '.', b.decode('ascii', errors='replace')))
    for idx in range(0, len(b) * 2, width * 2):
        h_b_l = []
        addr = '{:08x}'.format(idx)
        for id in range(idx, idx+(width * 2), 2):
            h_b_l.append(h_b[id:id+2])
        l = ' '.join(h_b_l)

        l_fill = width * 3  - len(l)
        print('{}: {}{}  |{}|'.format(addr, l, ' ' * l_fill, ''.join(lascii[int(idx/2):int(idx/2+width)])))

def _print_bytes_hex(b):
    print_hex(b)


_pr_debug = False

class CborAttr(object):

    _indent = 3

    @staticmethod
    def enable_debug():
        _pr_debug = True

    @staticmethod
    def encode(values):
        enc = CborEncoder()
        #enc.init(512)

        if not isinstance(values, (dict, list)):
            raise ValueError('dict or list expected: ' + str(type(values)))
        CborAttr._encode_recursive_container(enc, values, 1)

        v_enc = enc.bytes()
        if _pr_debug:
            print('encoded: ', v_enc)
            print('')
            print('len', len(v_enc))
            _print_bytes_hex(v_enc)
        return v_enc

    @staticmethod
    def _encode_recursive_container(enc, cont, indent):
        # cont_enc: CborEncoder
        if isinstance(cont, dict):

            length = len(cont)
            # key less special case, ignore
            if b'\x00' in cont:
                length -= 1

            # if b'\x00' in cont:
            #     length += (len(cont[b'\x00']) - 1)

            cont_enc = enc.encoder_create_map(length)
            cont_enc = enc
            if _pr_debug:
                # print(enc.bytes())
                print(' '*indent, 'recursing map, len:', length)
                print(' '*indent, '          map:', str(cont))

            for k, val in cont.items():
                # key less special case, ignore
                if k == b'\x00':
                    continue

                if _pr_debug:
                    print(' '*indent, 'Adding key:', str(k))
                CborAttr._encode_value(cont_enc, k, indent)
                # length -= 1
                if _pr_debug:
                    print(' '*indent, 'Adding val:', str(val))
                if isinstance(val, dict) or isinstance(val, list):
                    CborAttr._encode_recursive_container(cont_enc, val, indent + 3)
                    length -= 1
                else:
                    CborAttr._encode_value(cont_enc, val, indent)
                    length -= 1

            # if b'\x00' in cont:

            #     for val in cont[b'\x00']:
            #         if isinstance(val, dict) or isinstance(val, list):
            #             CborAttr._encode_recursive_container(cont_enc, val, indent + 3)
            #             length -= 1
            #         else:
            #             print(' '*indent, 'Adding special val:', str(val))
            #             CborAttr._encode_value(cont_enc, val, indent)
            #             length -= 1

        elif isinstance(cont, list):
            length = len(cont)
            cont_enc = enc.encoder_create_array(length)
            cont_enc = enc
            if _pr_debug:
                print(' '*indent, 'recursing array, len:', length)
                print(' '*indent, '          array:', str(cont))
            for val in cont:
                if _pr_debug:
                    print(' '*indent, 'Adding val:', str(val))
                if isinstance(val, dict) or isinstance(val, list):
                    CborAttr._encode_recursive_container(cont_enc, val, indent + 3)
                    length -= 1
                else:
                    CborAttr._encode_value(cont_enc, val, indent)
                    length -= 1
        else:
            raise ValueError('dict or list expected')
        if _pr_debug:
            print(' '*indent, 'Closeing container: ', str(type(cont)))
            print('Length remaining: ', length)
        cont_enc.encoder_close_container()


        #return cont

    @staticmethod
    def _encode_value(enc, value, indent):
        if isinstance(value, bytes):
            if _pr_debug:
                print('enc bytes', end=' ')
            enc.encode_byte_string(value)
        elif isinstance(value, str):
            if _pr_debug:
                print('enc str', end=' ')
            enc.encode_text_string(bytes(value, encoding='utf-8'))
        elif isinstance(value, int) and not isinstance(value, bool):
            if _pr_debug:
                print('enc int', end=' ')
            enc.encode_int(value)
        elif isinstance(value, bool):
            if _pr_debug:
                print('enc bool', end=' ')
            enc.encode_boolean(value)
        else:
            raise ValueError("cannot encode " + str(type(value)))

        if _pr_debug:
            print(' '*indent, 'encoded: ',str(type(value)), ' ', str(value))

    @staticmethod
    def decode(data):

        #parser = CborParser()
        #it = parser.init(data)
        it = CborDecoder(data)
        
        if it.at_end():
            if _pr_debug:
                print("Empty")
            return None

        _type = it.get_type()
        # if _type != CborType.Array and _type != CborType.Map:
        if _type != CborType.Map:
            if _pr_debug:
                print("Unxepected type", _type, 'expected top level container')
            return None

        # vals =  [ CborAttr._decode_container(it, 0)]
        vals = []
        while not it.at_end():
            _type = it.get_type()
            if _pr_debug:
                print("top level type", _type, '(expected top level container)')
            if _type == CborType.Array or _type == CborType.Map:
                vals.append(CborAttr._decode_container(it, 0))
            else:
                vals.append(CborAttr._decode_value(it, _type, 0))
                if not it.at_end():
                    it.advance()
        return vals

    @staticmethod
    def _decode_container(it, indent):
        if it.at_end():
            if _pr_debug:
                print("Empty")
            return None

        _type = it.get_type()
        if _pr_debug:
            print(' '*indent, "Container: ", str(_type))
        if _type == CborType.Array:
            cont = []
            if _pr_debug:
                print(' '*indent, "Array[" )
            if it.is_length_known():
                if _pr_debug:
                    print(' '*indent, "len:", it.get_array_length())
            else:
                if _pr_debug:
                    print(' '*indent, "len: ??")
            child = it.enter_container()
            child = it

            while not child.at_end():
                _type = child.get_type()
                if _pr_debug:
                    print(' '*indent,'Value>type:', str(_type), bytes([_type.value]).hex())

                if _type == CborType.Array or _type == CborType.Map:
                    cont.append(CborAttr._decode_container(child, indent + 2))
                elif _type == CborType.Invalid:
                    if _pr_debug:
                        print(' '*indent, "Parseerror, invalid type in array")
                    return cont
                else:
                    cont.append(CborAttr._decode_value(child, _type, indent + 2))
                    if not child.at_end():
                        child.advance()

            if _pr_debug:
                print(' '*indent, '] Leaving: ', str(child))
            it = child.leave_container()
            it = child
        elif _type == CborType.Map:
            cont = {}
            key = None
            if _pr_debug:
                print(' '*indent, "Map{")
            if it.is_length_known():
                if _pr_debug:
                    print(' '*indent, "len:", it.get_map_length())
            else:
                if _pr_debug:
                    print(' '*indent, "len: ??")
            child = it.enter_container()
            child = it

            while not child.at_end():
                _type = child.get_type()
                if _pr_debug:
                    print(' '*indent,'Key type:', str(_type), bytes([_type.value]).hex())

                if _type == CborType.TextString:
                    key = CborAttr._decode_value(child, _type, indent + 2)
                    #key = child.get_text_string()
                    if _pr_debug:
                        print(' '*indent, 'key', key)

                    if not child.at_end():
                        child.advance()
                elif _type == CborType.Invalid:
                    if _pr_debug:
                        print(' '*indent, "Parseerror, invalid type for key in map")
                    return cont
                else:
                    # allow keyless values, save under key b'\0x00'
                    if _pr_debug:
                        print(' '*indent, "Parse error, expected text sting for key, got", str(_type))
                        print(' '*indent, 'ignoring and continueing with keyless')
                    if not b'\x00' in cont:
                        cont[b'\x00'] = ( CborAttr._decode_value(child, _type, indent + 2), )

                    else:
                        cont[b'\x00'] = (*cont[b'\x00'], CborAttr._decode_value(child, _type, indent + 2))
                    if not child.at_end():
                        if _pr_debug:
                            print('Got more after err')
                        child.advance()
                        continue
                    else:
                        if _pr_debug:
                            print('Got no more items after err')
                        return cont


                if child.at_end():
                    if _pr_debug:
                        print(' '*indent, 'Parse error, expected value for Map key', key)

                _type = child.get_type()

                if _type == CborType.Array or _type == CborType.Map:
                    cont[key] = CborAttr._decode_container(child, indent + 2)
                elif _type == CborType.Invalid:
                    if _pr_debug:
                        print(' '*indent, "Parse error, invalid type for value in map")
                    return cont
                else:
                    cont[key] = CborAttr._decode_value(child, _type, indent + 2)
                    if not child.at_end():
                        child.advance()
                key = None

            if _pr_debug:
                print(' '*indent, '} Leaving: ', str(child))
            it = child.leave_container()
            it = child
        return cont

    @staticmethod
    def _decode_value(it, _type, indent):
        if _pr_debug:
            print(' '*indent,'Value type:', str(_type), bytes([_type.value]).hex())
        val = it.get_value()

        if _pr_debug:
            print(' '*indent, "Val: ", str(val))
        return val

