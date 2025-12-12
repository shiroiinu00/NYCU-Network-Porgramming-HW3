import argparse, socket, threading, tkinter as tk
from tkinter import messagebox
from .protocol import send_json, recv_json

class TTTApp(tk.Tk):
    def __init__(self, sock, username):
        super().__init__()
        self.sock = sock
        self.username = username
        self.mark = None
        self.buttons = []
        self.status = tk.StringVar(value="Waiting for server...")
        self.title(f"TicTacToe - {username}")
        grid = tk.Frame(self); grid.pack(padx=10, pady=10)
        for i in range(9):
            btn = tk.Button(grid, text="", width=6, height=3,
                            command=lambda idx=i: self.send_move(idx), state="disabled")
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
            self.buttons.append(btn)
        tk.Label(self, textvariable=self.status).pack(pady=6)
        threading.Thread(target=self.listen_loop, daemon=True).start()

    def listen_loop(self):
        while True:
            try:
                msg = recv_json(self.sock)
            except:
                result = messagebox.showerror("Announcement", "One of the oppoents disconnected. The game will stop and return to the lobby")
                if result:
                    self.destroy()
                break
            if msg is None:
                result = messagebox.showerror("Announcement", "One of the oppoents disconnected. The game will stop and return to the lobby")
                if result:
                    self.destroy()
                break
            cmd = msg.get("cmd")
            if cmd == "ask_move":
                board = msg.get("board", [""]*9)
                self.mark = msg.get("mark") if msg.get("turn_user")==self.username else self.mark
                self.after(0, lambda b=board, turn=msg.get("turn_user"): self.update_board(b, turn))
            elif cmd == "board_update":
                self.after(0, lambda b=msg.get("board", [""]*9), nxt=msg.get("next"): self.update_board(b, nxt))
            elif cmd == "game_over":
                board = msg.get("board", [""]*9)
                winner = msg.get("winner")
                text = "Draw" if not winner else f"{winner} wins"
                self.after(0, lambda b=board, t=text: self.handle_game_over(b, t))
                break
            elif cmd == "error":
                self.after(0, lambda m=msg.get("message","error"): messagebox.showerror("Error", m))

    def update_board(self, board, turn_user):
        for i,val in enumerate(board):
            self.buttons[i]["text"] = val
        if turn_user == self.username:
            self.status.set("Your turn")
            for i,val in enumerate(board):
                self.buttons[i]["state"] = "normal" if not val else "disabled"
        else:
            self.status.set(f"Waiting for {turn_user or 'result'}")
            self.disable_all()

    def disable_all(self):
        for b in self.buttons: b["state"] = "disabled"

    def send_move(self, idx):
        send_json(self.sock, {"cmd":"move","cell": idx})
        self.disable_all()

    def handle_game_over(self, board, text):
        self.update_board(board, None)
        self.disable_all()
        result = messagebox.showinfo("Game Over", text)
        if result == "ok":
            self.destroy()

def main(host, port, username, room_id, token):
    sock = socket.create_connection((host, port))
    send_json(sock, {"cmd":"join","username":username,"room_id":room_id,"token":token})
    app = TTTApp(sock, username)
    app.mainloop()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23456)
    ap.add_argument("--user", default="player")
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()
    main(args.host, args.port, args.user, args.room_id, args.token)
