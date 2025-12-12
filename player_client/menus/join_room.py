import tkinter as tk
from tkinter import messagebox


class JoinRoomFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Join Room", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=10
        )

        tk.Label(self, text="Room ID:").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.entry_room_id = tk.Entry(self, width=20)
        self.entry_room_id.grid(row=1, column=1, padx=10, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(
            btn_frame, text="Join", width=10,
            command=self.on_join
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="Back", width=10,
            command=lambda: controller.show_frame("PlayerHomeFrame")
        ).grid(row=0, column=1, padx=5)

    def on_join(self):
        room_id_str = self.entry_room_id.get().strip()
        if not room_id_str:
            messagebox.showwarning("Input error", "Room ID is required.")
            return

        try:
            room_id = int(room_id_str)
        except ValueError:
            messagebox.showwarning("Input error", "Room ID must be an integer.")
            return
        

        try:
            resp = self.controller.lobby_client.request({
                "cmd": "join_room",
                "room_id": room_id,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if resp.get("ok"):
            # username = self.controller.get_current_user()
            # check_result = self.controller.lobby_client.check_vlocal_higher_vstore(username, resp.get("game_id"))
            # print(f"check_result: {check_result}")
            # if  check_result == 0:
            #     messagebox.showerror("Create room", "You have to install the latest version before create a room.")
            #     self.controller.show_frame("GameStoreFrame")
            #     return
            # elif check_result == -1:
            #     messagebox.showerror("Create room", "You don't have the game. Please select other games or installed the game first")
            #     return
            self.controller.set_current_room({
                "room_id": room_id,
                "game_id": None,       
                "game_name": f"Room {room_id}",
                "max_players": None,
            })
            msg = resp.get("message", "Joined room.")
            self.controller.set_status(f"In room #{room_id}")
            messagebox.showinfo("Join room", msg)
            room = self.controller.get_current_room()
            room["players"] = resp.get("players")
            self.controller.set_current_room(room)

            self.controller.show_frame("RoomWaitFrame")
        else:
            msg = resp.get("message", "Failed to join room.")
            self.controller.set_status(f"Join room FAIL: {msg}")
            messagebox.showerror("Join room failed", f"{msg})")
