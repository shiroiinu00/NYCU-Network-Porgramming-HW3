import tkinter as tk
from tkinter import messagebox


class RoomWaitFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller


        self.label_title = tk.Label(self, text="Room Waiting", font=("Arial", 14, "bold"))
        self.label_title.pack(pady=(10, 5))

        self.label_room = tk.Label(self, text="Room: -", font=("Arial", 12))
        self.label_room.pack(pady=(0, 5))

        self.label_game = tk.Label(self, text="Game: -", font=("Arial", 11))
        self.label_game.pack(pady=(0, 10))

        tk.Label(self, text="Players in room:").pack()
        self.listbox_players = tk.Listbox(self, width=30, height=6)
        self.listbox_players.pack(pady=5)

        self.btn_frame = tk.Frame(self)
        self.btn_frame.pack(pady=10)

        # tk.Button(
        #     btn_frame, text="Start Game", width=10,
        #     command=self.on_start_game
        # ).grid(row=0, column=0, padx=5)

        # tk.Button(
        #     btn_frame, text="Leave Room", width=10,
        #     command=self.on_leave_room
        # ).grid(row=0, column=1, padx=5)
    


    def on_show(self):
        room = self.controller.get_current_room()
        user = self.controller.get_current_user()
        host = room.get("host")

        if not room:
            self.label_room.config(text="Room: (none)")
            self.label_game.config(text="Game: -")
            self.listbox_players.delete(0, tk.END)
            self.controller.set_status("No room joined.")
            return

        room_id = room["room_id"]
        game_name = room.get("game_name", f"Game {room['game_id']}")
        max_players = room.get("max_players", "?")

        self.label_room.config(text=f"Room #{room_id}  (max {max_players})")
        self.label_game.config(text=f"Game: {game_name}")
        self.controller.set_status(f"In room #{room_id}, waiting for players...")

        # self.listbox_players.delete(0, tk.END)
        # if user:
        #     self.listbox_players.insert(tk.END, f"{user} (host)")
        self.render_players()


        btn_frame = self.btn_frame

        if user == host:
            tk.Button(
                btn_frame, text="Start Game", width=10,
                command=self.on_start_game
            ).grid(row=0, column=0, padx=5)

            tk.Button(
                btn_frame, text="Leave Room", width=10,
                command=self.on_leave_room
            ).grid(row=0, column=1, padx=5)
        else:
            tk.Button(
                btn_frame, text="Leave Room", width=10,
                command=self.on_leave_room
            ).grid(row=0, column=1, padx=5)

        self.on_refresh()
        
        

    def on_refresh(self):
        room = self.controller.get_current_room()
        if not room:
            messagebox.showwarning("No room", "You are not in any room")
            return

        room_id = room["room_id"]
        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "room_info",
                "room_id": room_id,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))

        if not resp.get("ok"):
            msg = resp.get("message", "Failed to fetch room info.")
            messagebox.showerror("Room info", f"{msg})")
            return

        players = resp.get("players", [])
        room["players"] = players
        self.controller.set_current_room(room)
        self.render_players()

    def on_start_game(self):
        room = self.controller.get_current_room()
        if not room:
            messagebox.showwarning("Start game", "No room joined.")
            return

        room_id = room.get("room_id")
        try:
            resp = self.controller.lobby_client.send({
                "cmd": "start_game",
                "room_id": room_id,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return


    def on_leave_room(self):
        room = self.controller.get_current_room()
        if not room:
            self.controller.show_frame("PlayerHomeFrame")
            return

        room_id = room["room_id"]

        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "leave_room",
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
        
        if resp.get("ok"):
            msg = resp.get("message", "Left room.")
            self.controller.set_status(msg)
        else:
            msg = resp.get("message", "Failed to leave room")
            self.controller.set_status(f"Leave room FAIL: {msg}")
            messagebox.showerror("Leave room failed", f"{msg}")
        
        self.controller.set_current_room(None)
        self.controller.show_frame("PlayerHomeFrame")
        

    def render_players(self):
        room = self.controller.get_current_room()
        if not room:
            self.listbox_players.delete(0, tk.END)
            return
        host = room.get("host")
        players = room.get("players")
        print("test join currently", players)

        self.listbox_players.delete(0, tk.END)

        if players:
            for name in players:
                if name == host:
                    self.listbox_players.insert(tk.END, f"{name}(host)")
                else:
                    self.listbox_players.insert(tk.END, name)
        else:
            user = self.controller.get_current_user()
            if host:
                self.listbox_players.insert(tk.END, f"{host}(host)")
            if user and user != host:
                self.listbox_players.insert(tk.END, user)

    def render_players_from_current_room(self):
        room = self.controller.get_current_room()
        self.listbox_players.delete(0, tk.END)

        if not room:
            return
        
        host = room.get("host")
        players = room.get("players")

        if players:
            for name in players:
                if name == host:
                    self.listbox_players.insert(tk.END, f"{name}(host)")
                else:
                    self.listbox_players.insert(tk.END, name)

        else:
            user = self.controller.get_current_user()
            if host:
                self.listbox_players.insert(tk.END, f"{host}(host)")
            if user and user != host:
                self.listbox_players.insert(tk.END, user)

