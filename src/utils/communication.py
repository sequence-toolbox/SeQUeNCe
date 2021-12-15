from json import dumps, loads
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from socket import socket

LEN_BYTE_LEN = 4
BYTE_ORDER = "big"


def send_msg_with_length(socket: "socket", msg: Any):
    msg_byte = dumps(msg)
    data = len(msg_byte).to_bytes(LEN_BYTE_LEN, BYTE_ORDER) + msg_byte.encode(
        'utf-8')
    socket.sendall(data)


def recv_msg_with_length(socket: "socket") -> Any:
    length_byte = socket.recv(LEN_BYTE_LEN)
    length = int.from_bytes(length_byte, BYTE_ORDER)
    all_data = ''
    while len(all_data) < length:
        received_data = socket.recv(length)
        if all_data == '':
            all_data = received_data
        else:
            all_data += received_data
    received_msg = loads(all_data)
    return received_msg
