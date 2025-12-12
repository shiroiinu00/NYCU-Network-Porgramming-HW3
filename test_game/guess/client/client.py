import argparse, socket, threading, tkinter as tk
from tkinter import messagebox
from .protocol import send_json, recv_json

class GuessApp(tk.Tk):
    def __init__(self, sock, username):
        super().__init__()
        self.sock = sock
        self.username = username
        self.title(f"Guess Number - {username}")
        self.status = tk.StringVar(value="Waiting for server...")
        self.history = tk.StringVar(value="")
        self.input_var = tk.StringVar()

        top = tk.Frame(self); top.pack(padx=10, pady=10)
        tk.Label(top, textvariable=self.status).pack(anchor="w")
        entry_row = tk.Frame(top); entry_row.pack(fill="x", pady=6)
        tk.Entry(entry_row, textvariable=self.input_var, width=10).pack(side="left")
        self.btn = tk.Button(entry_row, text="Guess", state="disabled",
                             command=self.send_guess)
        self.btn.pack(side="left", padx=6)
        self.log = tk.Text(top, width=40, height=12, state="disabled")
        self.log.pack()

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
            if cmd == "ask_guess":
                turn_user = msg.get("turn_user")
                attempts_left = msg.get("attempts_left")
                history = msg.get("history", [])
                rng = msg.get("range") or [0, 100]
                self.after(0, lambda t=turn_user, a=attempts_left, h=history: self.on_turn(t, a, h, rng))
                self.input_var.set("")
            elif cmd == "guess_result":
                self.after(0, lambda m=msg: self.on_result(m))
            elif cmd == "game_over":
                self.after(0, lambda m=msg: self.on_game_over(m))
                break
            elif cmd == "error":
                self.after(0, lambda m=msg.get("message","error"): messagebox.showerror("Error", m))

    def on_turn(self, turn_user, attempts_left, history, range):
        self.render_history(history)
        if turn_user == self.username:
            self.status.set(f"Your turn ({attempts_left} left), range: {range[0]} - {range[1]}")
            self.btn["state"] = "normal"
        else:
            self.status.set(f"Waiting for {turn_user} ({attempts_left} left)")
            self.btn["state"] = "disabled"

    def on_result(self, msg):
        self.render_history(msg.get("history", []))
        next_user = msg.get("next")
        hint = msg.get("hint")
        by = msg.get("by")
        self.status.set(f"{by} guessed {msg.get('value')} -> {hint}. Next: {next_user or 'done'}")
        self.btn["state"] = "disabled"

    def on_game_over(self, msg):
        self.render_history(msg.get("history", []))
        winner = msg.get("winner")
        target = msg.get("target")
        text = "Draw! " if not winner else f"{winner} wins! "
        text += f"Target was {target}"
        res = messagebox.showinfo("Game Over", text)
        if res == "ok":
            self.destroy()

    def render_history(self, history):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for item in history:
            self.log.insert("end", f"{item['user']} -> {item['value']} ({item['hint']})\n")
        self.log.configure(state="disabled")

    def send_guess(self):
        try:
            val = int(self.input_var.get().strip())
        except Exception:
            messagebox.showerror("Error", "Please enter a number"); return
        send_json(self.sock, {"cmd":"guess","value": val})
        self.btn["state"] = "disabled"

def main(host, port, username, room_id, token):
    sock = socket.create_connection((host, port))
    send_json(sock, {"cmd":"join","username":username,"room_id":room_id,"token":token})
    app = GuessApp(sock, username)
    app.mainloop()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=45678)
    ap.add_argument("--user", default="player")
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()
    main(args.host, args.port, args.user, args.room_id, args.token)
