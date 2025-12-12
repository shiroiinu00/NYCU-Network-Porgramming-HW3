from __future__ import annotations

import socket
import json
import threading
import queue
import itertools


from typing import Dict, Any, Callable, Optional, List
from pathlib import Path
from tkinter import messagebox

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

    def register_player(self, username, password, display_name=None):
        req = {
            "cmd": "player_register",
            "username": username,
            "password": password,
        }
        return self.send_request(req)

    def login_player(self, username, password):
        req = {
            "cmd": "player_login",
            "username": username,
            "password": password,
        }
        return self.send_request(req)
    
    def get_game_detail(self, game_id: int):
        return self.send_request({
            "cmd": "get_game_detail",
            "game_id": game_id
        })
    
    def add_rating(self, game_id: int, score: int, comment: str):
        return self.send_request({
            "cmd": "add_rating",
            "game_id": game_id,
            "score": score,
            "comment": comment,
        })
    
    
    def check_vlocal_higher_vstore(self, username: str, store_game_id: int):
        try:
            resp = self.send_request({"cmd": "list_games"})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return
        if not resp.get("ok"):
            return
        
        games = resp.get("games", [])
        latest_ver = next(
            (g.get("latest_version") for g in games if g.get("game_id") == store_game_id),
            None,
        )
        if latest_ver is None:
            return -2 

        local_game_version = "0.0.0"
        find = False
        # print(f"user: {username}, games: {get_user_games(username)}")
        for local_game in get_user_games(username):
            if local_game["game_id"] == store_game_id:
                local_game_version = local_game["version"]
                find = True
                break
        if not find:
            return -1
        # print(f"username:{username}, local: {local_game_version}, latest: {latest_ver}, cmp {(cmp_ver(local_game_version, latest_ver) >=0)}")
        return 1 if (cmp_ver(local_game_version, latest_ver) >=0) else 0


def load_connection_info():
    _config_path = Path(__file__).parent / "config.json"

    with _config_path.open("r", encoding="utf-8") as f:
        _cfg = json.load(f)
    global LOBBY_PORT, LOBBY_HOST, FILE_HOST, FILE_PORT
    LOBBY_HOST = str(_cfg["LOBBY_HOST"])
    LOBBY_PORT = int(_cfg["LOBBY_PORT"])
    FILE_HOST = str(_cfg["FILE_HOST"])
    FILE_PORT = int(_cfg["FILE_PORT"])

    print(f"Host: {LOBBY_HOST}/ {type(LOBBY_HOST)}, Port: {LOBBY_PORT} / {type(LOBBY_PORT)}")

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
            # print(f"version: {version}")
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

def download_file_from_server(download_path: str, dest: Path):
    header = {
        "action": "download",
        "download_path": download_path
    }
    if not FILE_HOST or FILE_PORT is None:
        raise RuntimeError("FILE_HOST/FILE_PORT not configured; call load_connection_info() first")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((FILE_HOST, FILE_PORT))
        f = sock.makefile("rb")

        sock.sendall((json.dumps(header) + "\n").encode("utf-8"))

        line = f.readline()
        if not line:
            raise RuntimeError("no ack from file server")
        ack = json.loads(line.decode("utf-8"))
        if not ack.get("ok"):
            raise RuntimeError(f"file server refused: {ack}")
        
        file_size = int (ack["file_size"])

        remaining = file_size
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as out:
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    raise RuntimeError("connection closed mid-file")
                out.write(chunk)
                remaining -= len(chunk)
        return {
            "ok": True,
            "stored_path": str(dest),
            "bytes": file_size
        }

        
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


        






    
