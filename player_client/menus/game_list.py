import tkinter as tk
from tkinter import messagebox
from ..api_client import get_user_games


class GameListFrame(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="My Games", font=("Arial", 14, "bold")).pack(pady=10)

        self.listbox = tk.Listbox(self, width=40, height=8)
        self.listbox.pack(padx=10, pady=5)

        self.info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.info_var, fg="gray").pack(pady=(0, 5))

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Create Room", width=12,
            command=self.on_create_room
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="Back", width=12,
            command=lambda: controller.show_frame("PlayerHomeFrame")
        ).grid(row=0, column=1, padx=5)

        self.current_games: list[dict] = []

    def on_show(self):
        username = self.controller.get_current_user()
        if not username:
            self.info_var.set("Not logged in.")
            self.listbox.delete(0, tk.END)
            return

        try: 
            resp = self.controller.lobby_client.send_request({"cmd": "list_games"})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        store_games = resp.get("games", [])
        active_ids = {g.get("game_id") for g in store_games}

        local_games = get_user_games(username)
        local_games = [g for g in local_games if g.get("game_id") in active_ids]


        self.current_games = local_games
        self.listbox.delete(0, tk.END)
       

        if not local_games:
            self.info_var.set("No games installed for this user.")
            return

        for g in local_games:
            text = f"[{g['game_id']}] {g['name']} (v{g['version']})"
            self.listbox.insert(tk.END, text)

        self.info_var.set(f"{len(local_games)} game(s) installed.")

    def _get_selected_game(self):
        idxs = self.listbox.curselection()
        if not idxs:
            return None
        idx = idxs[0]
        if idx < 0 or idx >= len(self.current_games):
            return None
        return self.current_games[idx]

    def on_create_room(self):
        game = self._get_selected_game()
        if not game:
            messagebox.showwarning("Select game", "Please select a game first.")
            return

        game_id = game["game_id"]
        max_players = 2
        
        username = self.controller.get_current_user()
        check_result = self.controller.lobby_client.check_vlocal_higher_vstore(username, game_id)
        if  check_result == 0:
            messagebox.showerror("Create room", "You have to install the latest version before create a room.")
            self.controller.show_frame("GameStoreFrame")
            return
        elif check_result == -1:
            messagebox.showerror("Create room", "You don't have the game. Please select other games or installed the game first")
            return
        elif check_result == -2:
            messagebox.showinfo("Create room", "The game is deprecated on the store. However, you can still played the game with other players whose game version is same")
            return

        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "create_room",
                "game_id": game_id,
                "max_players": max_players,
                "game_version": game["version"],
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if resp.get("ok"):
            room_id = resp.get("room_id")
            msg = f"Room #{room_id} created for game {game_id} ({game['name']})."
            self.controller.set_status(msg)
            messagebox.showinfo("Room created", msg)
            self.controller.set_current_room({
                "room_id": room_id,
                "game_id": game_id,
                "game_name": game["name"],
                "max_players": max_players,
                "host": self.controller.get_current_user(), 
            })
            self.controller.show_frame("RoomWaitFrame")
        else:
            msg = resp.get("message", "Failed to create room.")
            self.controller.set_status(f"Create room FAIL: {msg}")
            messagebox.showerror("Create room failed", f"{msg}\n(code: {resp.get('error')})")
