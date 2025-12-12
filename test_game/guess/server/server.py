import argparse, random, socket, threading, traceback, time
from typing import Optional, List, Dict
from .protocol import send_json, recv_json

class GuessServer:
    def __init__(self, host, port, room_id=None, token=None, min_players=2, max_players=3,
                 max_attempts=20, low=1, high=100, start_wait=10.0):
        self.host, self.port = host, port
        self.room_id, self.token = room_id, token
        self.min_players, self.max_players = min_players, max_players
        self.max_attempts = max_attempts
        self.low, self.high = low, high
        self.low_range, self.high_range = low, high
        self.start_wait = start_wait
        self.players: List[Dict] = []  # {sock, username}
        self.lock = threading.Lock()
        self.running = True
        self.target = random.randint(self.low, self.high)
        self.history = []  # list of dicts: {user, value, hint}

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(self.max_players)
        srv.settimeout(0.5)
        print(f"[GUESS] listening on {self.host}:{self.port}, room={self.room_id}")
        try:
            join_deadline = None
            while self.running:
                with self.lock:
                    if len(self.players) >= self.max_players:
                        break
                    if len(self.players) >= self.min_players and join_deadline is None:
                        join_deadline = time.time() + self.start_wait
                    if join_deadline and time.time() >= join_deadline:
                        break
                try:
                    c, addr = srv.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self.handle_client, args=(c, addr), daemon=True).start()

            with self.lock:
                if len(self.players) < self.min_players:
                    return
            self.game_loop()
        except Exception:
            traceback.print_exc()
        finally:
            srv.close()
            print("[GUESS] server closed")

    def handle_client(self, sock: socket.socket, addr):
        try:
            join_msg = recv_json(sock)
            if not join_msg or join_msg.get("cmd") != "join":
                sock.close(); return
            if self.token and join_msg.get("token") != self.token:
                send_json(sock, {"cmd":"error","message":"bad token"}); sock.close(); return
            if self.room_id is not None and join_msg.get("room_id") != self.room_id:
                send_json(sock, {"cmd":"error","message":"wrong room"}); sock.close(); return
            username = join_msg.get("username") or f"player{len(self.players)+1}"
            with self.lock:
                if len(self.players) >= self.max_players:
                    send_json(sock, {"cmd":"error","message":"room full"}); sock.close(); return
                self.players.append({"sock": sock, "username": username})
            print(f"[GUESS] {username} joined from {addr}")
        except Exception as e:
            print(f"[GUESS] client error {addr}: {e}")

    def broadcast(self, obj):
        for p in list(self.players):
            try:
                send_json(p["sock"], obj)
            except Exception:
                try: p["sock"].close()
                finally: self.players.remove(p)

    def game_loop(self):
        turn = 0
        attempts_left = self.max_attempts
        while self.running and attempts_left > 0 and len(self.players) > 0:
            current = self.players[turn % len(self.players)]
            ask = {
                "cmd": "ask_guess",
                "turn_user": current["username"],
                "range": [self.low, self.high],
                "attempts_left": attempts_left,
                "history": self.history,
                "players": [p["username"] for p in self.players],
            }
            self.broadcast(ask)
            msg = recv_json(current["sock"])
            if not msg or msg.get("cmd") != "guess":
                self.running = False
                break
            try:
                value = int(msg.get("value"))
            except Exception:
                value = None
            if value is None or value < self.low or value > self.high:
                send_json(current["sock"], {"cmd":"error","message":"invalid guess"})
                continue


            attempts_left -= 1
            if value == self.target:
                hint = "correct"
                next_user = None
                self.history.append({"user": current["username"], "value": value, "hint": hint})
                self.broadcast({
                    "cmd": "guess_result",
                    "by": current["username"],
                    "value": value,
                    "hint": hint,
                    "next": next_user,
                    "attempts_left": attempts_left,
                    "history": self.history,
                })
                self.broadcast({
                    "cmd": "game_over",
                    "winner": current["username"],
                    "target": self.target,
                    "history": self.history,
                })
                return
            elif value < self.target:
                self.low = value
                hint = f"higher (range: {self.low}-{self.high})"
            else:
                self.high = value
                hint = f"lower (range: {self.low}-{self.high})"
            self.history.append({"user": current["username"], "value": value, "hint": hint})
            next_user = self.players[(turn + 1) % len(self.players)]["username"]
            self.broadcast({
                "cmd": "guess_result",
                "by": current["username"],
                "value": value,
                "hint": hint,
                "next": next_user,
                "attempts_left": attempts_left,
                "history": self.history,
            })
            turn += 1

        self.broadcast({
            "cmd": "game_over",
            "winner": None,
            "target": self.target,
            "history": self.history,
        })
        for p in self.players:
            try: p["sock"].close()
            except: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=45678)
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    ap.add_argument("--min-players", type=int, default=2)
    ap.add_argument("--max-players", type=int, default=5)
    ap.add_argument("--max-attempts", type=int, default=20)
    ap.add_argument("--low", type=int, default=1)
    ap.add_argument("--high", type=int, default=100)
    args = ap.parse_args()
    GuessServer(args.host, args.port, args.room_id, args.token,
                min_players=args.min_players, max_players=args.max_players,
                max_attempts=args.max_attempts, low=args.low, high=args.high).start()

if __name__ == "__main__":
    main()
