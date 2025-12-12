import json
import socket

def send_json(sock: socket.socket, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
    sock.sendall(data)

def recv_json(file_obj):
    line = file_obj.readline()
    if not line:
        return None
    return json.loads(line)