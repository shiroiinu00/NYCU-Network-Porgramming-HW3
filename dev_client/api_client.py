from __future__ import annotations

import socket
import json
import threading
import queue
import itertools


from typing import Dict, Any, Callable, Optional, List
from pathlib import Path

LOBBY_HOST = None
LOBBY_PORT = None
FILE_HOST = None
FILE_PORT = None

BASE_DIR = Path(__file__).resolve().parent
PLAYERS_DIR = BASE_DIR / "players"

class LobbyClient:

    def __init__(self, host: str = LOBBY_HOST, port: int = LOBBY_PORT) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.file = None
        self._recv_lock = threading.Lock()

        self._running = False
        self._listener_thread: Optional[threading.Thread] = None

        self._pending: Dict[int, "queue.Queue[Dict[str, Any]]"] = {}
        self._id_counter = itertools.count(1)

        self.on_event: Optional[Callable[[Dict[str, Any]], None]] = None

        self.connect()  

    def connect(self) -> None:
        if self.sock is not None:
            return  
        sock = socket.create_connection((self.host, self.port))
        self.sock = sock
        self.file = sock.makefile("r", encoding="utf-8")

        self._running = True
        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        self._listener_thread.start()

    def close(self) -> None:
        self._running = False
        if self.file is not None:
            try:
                self.file.close()
            except Exception:
                pass
            self.file = None

        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _listen_loop(self):
        try:
            while self._running:
                msg = self.recv()
                req_id = msg.get("req_id")
                if isinstance(req_id, int) and req_id in self._pending:
                    q = self._pending[req_id]
                    q.put(msg)
                    continue

                if self.on_event is not None:
                    self.on_event(msg)
        except Exception:
            pass

    def send(self, obj: Dict[str, Any]) -> None:
        if self.sock is None:
            raise RuntimeError("LobbyClient not connected. Call connect() first.")
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
        self.sock.sendall(data)
    
    def recv(self) -> Dict[str, Any]:
        if self.file is None:
            raise RuntimeError("LobbyClient not connected. Call connect() first.")
        line = self.file.readline()
        if not line:
            raise RuntimeError("server closed connection")
        print(line)
        return json.loads(line)
    
    def send_request(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        req_id = next(self._id_counter)
        obj = dict(obj)  # shallow copy
        obj["req_id"] = req_id

        q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._pending[req_id] = q

        self.send(obj)
        resp = q.get()  # blocking

        self._pending.pop(req_id, None)
        return resp

    def register_developer(self, username, password, display_name=None):
        req = {
            "cmd": "developer_register",
            "username": username,
            "password": password,
        }
        return self.send_request(req)

    def login_developer(self, username, password):
        req = {
            "cmd": "developer_login",
            "username": username,
            "password": password,
        }
        return self.send_request(req)
    
    def check_upload_version_valid(self, upload_version: str, latest_version: str):
        pu, pl = parse_ver(upload_version), parse_ver(latest_version)
        print(f"pu: {pu}, pl: {pl}")
        
        
        if len(pu) != len (pl) and len(pu) != 3:
            return -1
        
        if len(pl) == 1:
            return True
        
        for i in range(len(pu)):
            if pu[i - 1] < pl[i - 1]:
                return -2
            
        return True
        
    
    


def load_connection_info():
    _config_path = Path(__file__).parent / "config.json"

    with _config_path.open("r", encoding="utf-8") as f:
        _cfg = json.load(f)
    global LOBBY_PORT, LOBBY_HOST, FILE_HOST, FILE_PORT
    LOBBY_HOST = str(_cfg["LOBBY_HOST"])
    LOBBY_PORT = int(_cfg["LOBBY_PORT"])
    FILE_HOST = str(_cfg["FILE_HOST"])
    FILE_PORT = int(_cfg["FILE_PORT"])

    print(f"Lobby Host: {LOBBY_HOST}/ Lobby Port: {LOBBY_PORT} \n File Host: {LOBBY_HOST}/ File Port: {LOBBY_PORT}")

    return LOBBY_HOST, LOBBY_PORT

def get_user_games(username: str) -> List[Dict[str, Any]]:
    user_games_dir = PLAYERS_DIR / username / "games"
    games: List[Dict[str, Any]] = []

    if not user_games_dir.exists():
        return games
    
    for game_dir in user_games_dir.iterdir():
        if not game_dir.is_dir():
            continue

        meta_file = game_dir / "meta.json"
        if not meta_file.exists():
            continue

        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            game_id = int(data.get("game_id"))
            name = data.get("name", game_dir.name)
            version = data.get("version", "0.0.0")
        except Exception:
            continue

        games.append({
            "game_id": game_id,
            "name": name,
            "version": version,
            "path": str(game_dir)
        })
    games.sort(key=lambda g :g["game_id"])
    return games

def upload_file_to_server(zip_path: Path, upload_path: str, version: str):
    zip_path = Path(zip_path)
    file_size = zip_path.stat().st_size

    header = {
        "upload_path": upload_path,
        "file_size": file_size,
        "version": version
    }

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((FILE_HOST, FILE_PORT))
        f = sock.makefile("rb")

        sock.sendall((json.dumps(header) + "\n").encode("utf-8"))
        
        # recv ack
        line = f.readline()
        if not line:
            raise RuntimeError("no ack from file server")
        ack = json.loads(line.decode("utf-8"))
        if not ack.get("ok"):
            raise RuntimeError(f"file server refused: {ack}")
        
        with zip_path.open("rb") as rf:
            while True:
                chunk = rf.read(65536)
                if not chunk:
                    break
                sock.sendall(chunk)
        
        # recv success
        line2 = f.readline()
        if not line2:
            raise RuntimeError("no final response from file server")
        resp = json.loads(line2.decode("utf-8"))
        if not resp.get("ok"):
            raise RuntimeError(f"upload failed: {resp}")
        
        return resp
    
def parse_ver(v: str) -> tuple[int,...]:
    parts = (v or "0").split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return tuple(nums)

def cmp_ver(a: str, b: str) -> int:
    pa, pb = parse_ver(a), parse_ver(b)
    n = max(len(pa), len(pb))
    pa += (0,) * (n - len(pa))
    pb += (0,) * (n - len(pb))
    return (pa > pb) - (pa < pb) 








    
