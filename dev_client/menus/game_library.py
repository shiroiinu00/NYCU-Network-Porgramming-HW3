import tkinter as tk
from tkinter import messagebox

from ..api_client import get_user_games


class GameLibraryFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Game Store", font=("Arial", 14, "bold"), bg=self.controller.bg_color, fg=self.controller.fg_color,).pack(pady=10)

        self.listbox = tk.Listbox(self, width=70, height=10, bg="gray30", fg="white")
        self.listbox.pack(padx=10, pady=5)

        self.info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.info_var, bg=self.controller.bg_color, fg=self.controller.fg_color,).pack(pady=(0, 5))

        btn_frame = tk.Frame(self, bg=self.controller.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Update", width=10, bg="gray30", fg=self.controller.fg_color,
            command=self.on_update
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="Delete", width=10, bg="gray30", fg=self.controller.fg_color,
            command=self.on_delete
        ).grid(row=0, column=1, padx=5)

        
        tk.Button(
            btn_frame, text="Back", width=10, bg="gray30", fg=self.controller.fg_color,
            command=lambda: controller.show_frame("DeveloperHomeFrame")
        ).grid(row=0, column=2, padx=5)

        self.current_games: list[dict] = []

    def on_show(self):
        self.on_refresh()

    def on_refresh(self):
        username = self.controller.get_current_user()
        if not username:
            self.info_var.set("Not logged in.")
            self.listbox.delete(0, tk.END)
            return

        local_games = {g["game_id"]: g for g in get_user_games(username)}

        try:
            resp = self.controller.lobby_client.send_request({"cmd": "developer_list_games"})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            msg = resp.get("message", "Failed to list games.")
            self.info_var.set(msg)
            messagebox.showerror("List games", f"{msg})")
            return

        games = resp.get("games", [])
        self.current_games = games

        self.listbox.delete(0, tk.END)
        if not games:
            self.info_var.set("No games on server.")
            return

        for g in games:
            gid = g["game_id"]
            name = g.get("game_name", f"Game {gid}")
            latest_ver = g.get("latest_version") or "Not Upload to store"
            local = local_games.get(gid)

            if local is None:
                status = "Not installed"
                local_ver = "-"
            else:
                local_ver = local.get("version", "0.0.0")
                if g.get("latest_version") and local_ver != g["latest_version"]:
                    status = f"Installed v{local_ver}, update available"
                else:
                    status = f"Installed v{local_ver}"

            line = f"[{gid}] {name} | latest: {latest_ver}"
            self.listbox.insert(tk.END, line)

        self.info_var.set(f"You have {len(games)} game(s) on server.")
    
    def on_delete(self):
        g = self._get_selected_game()
        if not g:
            messagebox.showwarning("Select game", "Please select a game first.")
            return
        gid = g["game_id"]
        name = g.get("game_name")
        if not messagebox.askyesno("Delete game", f"Delete {name} (ID {gid}) from store?"):
            return
        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "developer_delete_game",
                "game_id": gid,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return
        
        if not resp.get("ok"):
            messagebox.showerror("Delete failed", resp.get("message", "Failed to delete"))
            return
        
        messagebox.showinfo("Delete game", f"{name} (ID {gid}) deleted from store.")
        self.on_refresh()
        



    def _get_selected_game(self):
        idxs = self.listbox.curselection()
        if not idxs:
            return None
        idx = idxs[0]
        if idx < 0 or idx >= len(self.current_games):
            return None
        return self.current_games[idx]

    def on_update(self):
        g = self._get_selected_game()
        if not g:
            messagebox.showwarning("Select game", "Please select a game first.")
            return

        gid = g["game_id"]
        gname = g["game_name"]
        # name = g.get("game_name", f"Game {gid}")
        # latest_ver = g.get("latest_version")
        # latest_ver_id = g.get("latest_version_id")

        # if latest_ver is None or latest_ver_id is None:
        #     messagebox.showwarning("No version", "This game has no uploaded version yet.")
        #     return
        self.controller.select_game_id = gid
        self.controller.select_game_name = gname
        print(f"gid: {self.controller.select_game_id} - gname: {self.controller.select_game_name}")
        self.controller.show_frame("DevUploadFrame")

        
