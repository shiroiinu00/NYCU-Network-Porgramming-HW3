import tkinter as tk
from tkinter import messagebox

class GameDetailFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.game_id = None

        tk.Label(self, text="Game Detail", font=("Arial", 14, "bold")).pack(pady=10)

        self.lbl_title = tk.Label(self, text="", font=("Arial", 12, "bold"))
        self.lbl_title.pack()

        self.lbl_meta = tk.Label(self, text="", fg="gray")
        self.lbl_meta.pack(pady=2)

        self.txt_desc = tk.Text(self, width=70, height=6, state="disabled", wrap="word")
        self.txt_desc.pack(padx=10, pady=5)

        tk.Label(self, text="Player Comments", font=("Arial", 12, "bold")).pack(pady=(10, 4))

        self.comments = tk.Text(self, width=70, height=10, state="disabled", wrap="word")
        self.comments.pack(padx=10, pady=5)

        form = tk.Frame(self); form.pack(pady=5)
        tk.Label(form, text="Score (1-5):").grid(row=0, column=0, padx=5)
        self.entry_score = tk.Entry(form, width=5)
        self.entry_score.grid(row=0, column=1, padx=5)
        tk.Label(form, text="Comment:").grid(row=0, column=2, padx=5)
        self.entry_comment = tk.Entry(form, width=40)
        self.entry_comment.grid(row=0, column=3, padx=5)
        tk.Button(form, text="Submit", command=self.on_submit).grid(row=0, column=4, padx=5)

        tk.Button(self, text="Back", width=10,
                  command=lambda: controller.show_frame("GameStoreFrame")).pack(pady=10)

    def on_show(self):
        gid = self.controller.selected_game_id
        if gid is None:
            messagebox.showwarning("No game", "Please pick a game from store first.")
            self.controller.show_frame("GameStoreFrame")
            return
        self.game_id = gid
        self.load_detail()

    def load_detail(self):
        try:
            resp = self.controller.lobby_client.send_request({"cmd": "get_game_detail", "game_id": self.game_id})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            messagebox.showerror("Load failed", resp.get("message", "failed"))
            return

        g = resp.get("game", {})
        self.lbl_title.config(text=g.get("game_name", ""))
        meta = f"ID {g.get('game_id')} | latest: {g.get('latest_version') or 'N/A'} | max players: {g.get('max_players') or '-'}"
        self.lbl_meta.config(text=meta)

        self.txt_desc.config(state="normal")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert(tk.END, g.get("game_description") or "No description")
        self.txt_desc.config(state="disabled")

        self.render_comments(resp.get("ratings", []))

    def render_comments(self, ratings):
        self.comments.config(state="normal")
        self.comments.delete("1.0", tk.END)
        if not ratings:
            self.comments.insert(tk.END, "No comments yet.\n")
        else:
            for r in ratings:
                line = f"{r.get('player', 'Unknown')} | {r.get('score')}/5 | {r.get('created_at')}\n{r.get('comment')}\n\n"
                self.comments.insert(tk.END, line)
        self.comments.config(state="disabled")

    def on_submit(self):
        if self.game_id is None:
            return
        try:
            score = int(self.entry_score.get().strip())
        except ValueError:
            messagebox.showwarning("Input", "Score must be 1-5")
            return
        comment = self.entry_comment.get().strip()

        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "add_rating",
                "game_id": self.game_id,
                "score": score,
                "comment": comment,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            messagebox.showerror("Submit failed", resp.get("message", "failed"))
            return

        self.entry_comment.delete(0, tk.END)
        self.render_comments(resp.get("ratings", []))
        messagebox.showinfo("Thank you", "Rating submitted")
