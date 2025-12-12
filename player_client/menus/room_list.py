# player_client/gui/frames/room_list.py
import tkinter as tk
from tkinter import messagebox


class RoomListFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.info_var = tk.StringVar(value="")

        tk.Label(self, text="Available Rooms", font=("Arial", 14, "bold")).pack(pady=10)

        # 用 Listbox 顯示，簡單版: 每行一個房間
        self.listbox = tk.Listbox(self, width=60, height=8)
        self.listbox.pack(padx=10, pady=5)

        self.info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.info_var, fg="gray").pack(pady=(0, 5))

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Refresh", width=10,
            command=self.on_refresh
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="Join", width=10,
            command=self.on_join
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            btn_frame, text="Back", width=10,
            command=lambda: controller.show_frame("PlayerHomeFrame")
        ).grid(row=0, column=2, padx=5)

        self.current_rooms: list[dict] = []

    def on_show(self):
        self.on_refresh()

    def on_refresh(self):
        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "list_rooms",
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return
        if not resp.get("ok"):
            msg = resp.get("message", "Failed to list rooms.")
            self.info_var.set(msg)
            messagebox.showerror("List rooms", f"{msg})")
            return

        rooms = resp.get("rooms", [])
        self.current_rooms = rooms

        self.listbox.delete(0, tk.END)

        if not rooms:
            self.info_var.set("No open rooms.")
            return

        for r in rooms:
            room_id = r.get("room_id")
            host = r.get("host", "?")
            game_name = r.get("game_name", f"Game {r.get('game_id')}")
            cur = r.get("current_players", 0)
            mx = r.get("max_players", "?")
            text = f"Room #{room_id} | Host: {host} | Game: {game_name} | Players: {cur}/{mx}"
            self.listbox.insert(tk.END, text)

        self.info_var.set(f"{len(rooms)} room(s) available.")

    def _get_selected_room(self):
        idxs = self.listbox.curselection()
        if not idxs:
            return None
        idx = idxs[0]
        if idx < 0 or idx >= len(self.current_rooms):
            return None
        return self.current_rooms[idx]

    def on_join(self):
        room = self._get_selected_room()
        if not room:
            messagebox.showwarning("Select room", "Please select a room first.")
            return

        room_id = room["room_id"]
        game_id = room.get("game_id")

        username = self.controller.get_current_user()
        print(f"game_id: {game_id}")
        check_result = self.controller.lobby_client.check_vlocal_higher_vstore(username, game_id)
        print(f"check_result: {check_result}")
        if  check_result == 0:
            messagebox.showerror("Join room", "You have to install the latest version before join the room.")
            self.controller.show_frame("GameStoreFrame")
            return
        elif check_result == -1:
            messagebox.showerror("Join room", "You don't have the game. Please select other games or installed the game first")
            return
        elif check_result == -2:
            messagebox.showinfo("Join room", "The game is deprecated on the store. However, you can still played the game with other players whose game version is same")
            return

        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "join_room",
                "room_id": room_id,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return
        print(f"resp\n{resp}")
        if resp.get("ok"):            
            self.controller.set_current_room({
                "room_id": room_id,
                "game_id": room.get("game_id"),
                "game_name": room.get("game_name"),
                "max_players": room.get("max_players"),
                "host": room.get("host"),
            })
            msg = resp.get("message", "Joined room.")
            self.controller.set_status(f"In room #{room_id}")
            messagebox.showinfo("Join room", msg)
            self.controller.show_frame("RoomWaitFrame")
        else:
            msg = resp.get("message", "Failed to join room.")
            self.controller.set_status(f"Join room FAIL: {msg}")
            messagebox.showerror("Join room failed", f"{msg}. If this circumstance continues, you may refresh the page to ensure the room available")
