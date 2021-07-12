"""A simple script to get an open port for communication"""

import socket

s = socket.socket()
s.bind(('127.0.0.1', 0))
port = s.getsockname()[1]
s.close()
print(port)

