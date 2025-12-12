import argparse, socket, threading, traceback
from typing import Optional
from .protocol import send_json, recv_json

WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6)
]

def check_winner(board):
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
        
    return None

class TicTacToeServer:
    def __init__(self, host, port, room_id=None, token=None, min_players=2):
        self.host = host
        self.port = port
        self.token = token
        self.min_players = min_players
        self.room_id = room_id
        self.players = []
        self.lock = threading.Lock()
        self.board = [""] * 9
        self.turn = 0
        self.running = True

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(self.min_players)
        srv.settimeout(0.5)
        print(f"[TTT] listening on {self.host}: {self.port}, room={self.room_id}")
        try:
            while self.running:
                with self.lock:
                    if len(self.players) >= self.min_players: break
                    try:
                        c, addr = srv.accept()
                    except socket.timeout:
                        continue
                    threading.Thread(target=self.handle_client, args=(c, addr), daemon=True).start()
            
            if len(self.players) < 2:
                return
            with self.lock:
                self.players[0]["mark"] = "X"
                self.players[1]["mark"] = "O"
            self.loop_game()
        except Exception:
            traceback.print_exc()
        finally:
            srv.close()
            print("[TTT] server closed")
        
        
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
                if len(self.players) >= self.min_players:
                    send_json(sock, {"cmd":"error","message":"room full"}); sock.close(); return
                self.players.append({"sock": sock, "username": username, "mark": None})
            print(f"[TTT] {username} joined from {addr}")
        except Exception as e:
            print(f"[TTT] client error {addr}: {e}")

    def loop_game(self):
        while self.running:
            current = self.players[self.turn]
            ask = {
                "cmd": "ask_move",
                "board": self.board,
                "turn_user": current["username"],
                "mark": current["mark"]
            }
            self.broadcast(ask)
            msg = recv_json(current["sock"])
            if not msg or msg.get("cmd") != "move":
                self.running = False
                break
            idx = msg.get("cell")
            if not isinstance(idx, int) or idx < 0 or idx > 8 or self.board[idx]:
                send_json(current["sock"],{
                    "cmd": "error",
                    "message": "invalid move"
                })
                continue
            self.board[idx] = current["mark"]
            winner_mark = check_winner(self.board)
            is_full = all(self.board)
            next_user = self.players[1-self.turn]["username"]
            self.broadcast({
                "cmd": "board_update",
                "board": self.board,
                "last_move": idx,
                "by": current["username"],
                "mark": current["mark"],
                "next": None if winner_mark or is_full else next_user,
                "status": "ongoing" if not (winner_mark or is_full) else "finished"
            })

            if winner_mark or is_full:
                result = "draw"
                if winner_mark == self.players[0]["mark"]:
                    result = "p1"
                elif winner_mark == self.players[1]["mark"]:
                    result = "p2"
                self.broadcast({
                    "cmd": "game_over",
                    "board": self.board,
                    "result": result,
                    "winner": current["username"] if winner_mark else None
                })
                break
            self.turn = 1 - self.turn
        for p in self.players:
            try: p["sock"].close()
            except: pass



    def broadcast(self, obj):
        for p in list(self.players):
            try:
                send_json(p["sock"], obj)
            except Exception:
                p.get("sock").close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=34567)
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()
    TicTacToeServer(args.host, args.port, args.room_id, args.token).start()

if __name__ == "__main__":
    main()