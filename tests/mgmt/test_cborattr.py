import pytest

import cbor

_values = [
    ({},
        bytes([0xa0])
    ),
    ({'fooint': 0x0f00},
        b'\xa1ffooint\x19\x0f\x00'
    ),
    ({'foostr': 'foo'},
        b'\xa1ffoostrcfoo'
    ),
    # this fails, not good
    ({'fooarr': ['foo', 'bar']},
        b'\xa1ffooarr\x82cfoocbar'
    ),
    ({'foomap': { 'foo': 'bar'}},
        b'\xa1ffoomap\xa1cfoocbar'
    ),
    ({'foobool': True},
        b'\xa1gfoobool\xf5'
    ),
    ({'foobool': False},
        b'\xa1gfoobool\xf4'
    ),
]

@pytest.mark.parametrize('py_map, bin_value',
    _values
)
def test_encode(py_map, bin_value):
    map_enc = cbor.dumps(py_map)

    assert map_enc == bin_value


@pytest.mark.parametrize('py_map, bin_value',
    _values
)
@pytest.mark.timeout(timeout=5)
def test_decode(py_map, bin_value):
    map_dec = cbor.loads(bin_value)

    assert map_dec is not None
    # assert len(map_dec) != 0
    assert type(map_dec) == type(py_map), f"dec: {map_dec}"
    assert map_dec == py_map
