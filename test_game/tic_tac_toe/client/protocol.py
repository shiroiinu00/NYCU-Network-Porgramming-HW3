import json, socket
from typing import Optional

_buffer_map = {}

def send_json(sock: socket.socket, obj: dict) -> None:
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))


def recv_json(sock: socket.socket) -> Optional[dict]:
    if sock not in _buffer_map:
        _buffer_map[sock] = b""

    while True:
        if b"\n" in _buffer_map[sock]:
            line, _buffer_map[sock] = _buffer_map[sock].split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line.decode("utf-8"))
            except:
                continue

        chunk = sock.recv(4096)
        if not chunk:
            return None  # 真斷線
        _buffer_map[sock] += chunk
