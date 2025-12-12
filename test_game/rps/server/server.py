import argparse, socket, threading, traceback, time
from typing import Optional

from .protocol import send_json, recv_json, decide  # decide(a,b)->"p1"/"p2"/"draw"

MOVE_MAP = {
    "1": "rock",
    "2": "paper",
    "3": "scissors",
    "rock": "rock",
    "paper": "paper",
    "scissors": "scissors",
}


def normalize_move(raw) -> Optional[str]:
    if raw is None:
        return None
    return MOVE_MAP.get(str(raw).strip().lower())


def send_json_to_all(players, obj):
    for p in players:
        try:
            send_json(p["sock"], obj)
        except Exception:
            p["disconnected"] = True


class RPSServer:
    """
    Multi-round Rock-Paper-Scissors; first to reach win_score wins.
    """
    def __init__(self, host: str, port: int, room_id: Optional[int], token: Optional[str],
                 min_players=2, win_score=3):
        self.host = host
        self.port = port
        self.room_id = room_id
        self.token = token
        self.min_players = min_players
        self.win_score = win_score
        self.players = []  # [{sock, username, move}]
        self.lock = threading.Lock()
        self.scores = {"p1": 0, "p2": 0}
        self.round_num = 0
        self.running = True

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(self.min_players)
        srv.settimeout(0.5)
        print(f"[RPS] listening on {self.host}:{self.port}, room={self.room_id}")
        try:
            # Wait for players
            while self.running:
                with self.lock:
                    if len(self.players) >= self.min_players:
                        break
                try:
                    c, addr = srv.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self.handle_client, args=(c, addr), daemon=True).start()

            # Play multiple rounds until someone reaches win_score
            while self.running and len(self.players) >= self.min_players:
                self.round_num += 1
                send_json_to_all(self.players, {
                    "cmd": "round_start",
                    "round": self.round_num,
                    "scores": self.scores,
                })
                if not self.collect_moves():
                    break
                self.process_round()
                if self.is_game_end():
                    break
            self.game_over()
        except Exception:
            traceback.print_exc()
        finally:
            srv.close()
            print("[RPS] server closed")

    def handle_client(self, sock: socket.socket, addr):
        try:
            join_msg = recv_json(sock)
            if not join_msg or join_msg.get("cmd") != "join":
                sock.close()
                return
            if self.token and join_msg.get("token") != self.token:
                send_json(sock, {"cmd": "error", "message": "bad token"})
                sock.close()
                return
            if self.room_id is not None and join_msg.get("room_id") != self.room_id:
                send_json(sock, {"cmd": "error", "message": "wrong room"})
                sock.close()
                return

            username = join_msg.get("username") or f"player{len(self.players)+1}"
            with self.lock:
                if len(self.players) >= self.min_players:
                    send_json(sock, {"cmd": "error", "message": "room full"})
                    sock.close()
                    return
                self.players.append({"sock": sock, "username": username, "move": None})
            print(f"[RPS] {username} joined from {addr}")
        except Exception as e:
            print(f"[RPS] client error {addr}: {e}")

    def collect_moves(self):
        with self.lock:
            for p in self.players:
                p["move"] = None
                p["disconnected"] = False
        threads = []
        for p in self.players:
            t = threading.Thread(target=self.ask_and_wait_move, args=(p,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        with self.lock:
            if any(p.get("disconnected") for p in self.players):
                self.running = False
                return False
            return all(p["move"] is not None for p in self.players)

    def ask_and_wait_move(self, player):
        try:
            send_json(player["sock"], {"cmd": "ask_move", "round": self.round_num})
            msg = recv_json(player["sock"])
            if not msg:
                with self.lock:
                    print(player["sock"], "has the problem")
                    player["disconnected"] = True
                return
            print(player["username"], "send ", msg)
            raw_move = msg.get("move") if msg and msg.get("cmd") == "move" else None
            mv = normalize_move(raw_move) or "rock"
            with self.lock:
                player["move"] = mv
            print("Wait for other player selecting...")
        except Exception as e:
            print(f"[RPS] ask_move error: {e}")
            with self.lock:
                player["disconnected"] = True

    def process_round(self):
        if len(self.players) < 2:
            return
        p1, p2 = self.players[0], self.players[1]
        winner = decide(p1["move"], p2["move"])
        if winner == "p1":
            self.scores["p1"] += 1
        elif winner == "p2":
            self.scores["p2"] += 1
        payload = {
            "cmd": "round_result",
            "round": self.round_num,
            "p1": {"user": p1["username"], "move": p1["move"]},
            "p2": {"user": p2["username"], "move": p2["move"]},
            "winner": winner,  # p1/p2/draw
            "scores": self.scores,
        }
        send_json_to_all(self.players, payload)

    def is_game_end(self) -> bool:
        return self.scores["p1"] >= self.win_score or self.scores["p2"] >= self.win_score

    def game_over(self):
        if len(self.players) < 2:
            return
        p1, p2 = self.players[0], self.players[1]
        if self.scores["p1"] > self.scores["p2"]:
            result = "p1"
        elif self.scores["p2"] > self.scores["p1"]:
            result = "p2"
        else:
            result = "draw"
        payload = {
            "cmd": "game_over",
            "rounds": self.round_num,
            "scores": self.scores,
            "result": result,
            "p1": p1["username"],
            "p2": p2["username"],
        }
        send_json_to_all(self.players, payload)
        time.sleep(0.1)

        for p in self.players:
            try:
                p["sock"].shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                p["sock"].close()
            except:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=23456)
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    ap.add_argument("--win-score", type=int, default=3)
    args = ap.parse_args()
    RPSServer(args.host, args.port, args.room_id, args.token, win_score=args.win_score).start()


if __name__ == "__main__":
    main()
