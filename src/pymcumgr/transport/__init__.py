from .transport import Transport
from .ble_transport import TransportBLE

Transport.register(TransportBLE)
