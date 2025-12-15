import tkinter as tk
import json
import subprocess, sys, threading
from tkinter import messagebox
from pathlib import Path

from .api_client import load_connection_info, LobbyClient

from .menus.main_menu import MainMenuFrame
from .menus.auth import RegisterFrame, LoginFrame
from .menus.home import PlayerHomeFrame
from .menus.game_list import GameListFrame
from .menus.game_store import GameStoreFrame
from .menus.room_wait import RoomWaitFrame
from .menus.join_room import JoinRoomFrame
from .menus.room_list import RoomListFrame
from .menus.game_detail import GameDetailFrame


class PlayerClientApp(tk.Tk):
    def __init__(self, client: LobbyClient):
        super().__init__()

        self.title("HW3 Player Client")
        self.resizable(False, False)

        self.lobby_client = client
        self.lobby_client.on_event = self._on_server_event

        self.status_var = tk.StringVar(value="")
        self.current_user: str | None = None
        self.current_room: dict | None = None
        self.selected_game_id = None
        self.selected_game_name = None

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        status_label = tk.Label(self, textvariable=self.status_var, fg="gray")
        status_label.pack(side="bottom", pady=4)

        self.frames = {}
        for F in (MainMenuFrame, RegisterFrame, LoginFrame, PlayerHomeFrame, GameListFrame, RoomWaitFrame, JoinRoomFrame, RoomListFrame, GameStoreFrame, GameDetailFrame):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("MainMenuFrame")

        self.center_window()

        

    def center_window(self):
        w = 600
        h = 600
        self.update_idletasks() 

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = (screen_w - w) // 2
        y = (screen_h - h) // 2

        self.geometry(f"{w}x{h}+{x}+{y}")

    def show_frame(self, name: str):
        frame = self.frames[name]
        on_show = getattr(frame, "on_show", None)
        if callable(on_show):
            on_show()
        if name == "MainMenuFrame":
            self.set_status(f"")
        self.frames[name].tkraise()

    def set_status(self, text: str):
        self.status_var.set(text)
    
    def set_current_user(self, username: str):
        self.current_user = username

    def get_current_user(self) -> str:
        return self.current_user
    
    def set_current_room(self, room_info: dict):
        self.current_room = room_info
    
    def get_current_room(self) -> dict:
        return self.current_room
    
    # listening thread (background execution)
    def _on_server_event(self, msg: dict):
        self.after(0, self._dispatch_event_on_main_thread, msg)

    def _dispatch_event_on_main_thread(self, msg: dict):
        cmd = msg.get("cmd")
        if cmd == "force_logout":
            self.set_current_user(None)
            self.set_status("You were logged out by server.")
            tk.messagebox.showinfo("Force logout", msg.get("message", "You were logged out."))
            self.show_frame("MainMenuFrame")
        elif cmd == "room_update":
            print("enter room update")
            self.handle_room_update(msg)
        elif cmd == "room_closed":
            self.handle_room_closed(msg)
        elif cmd == "server_shutdown":
            messagebox.showinfo("Server", msg.get("message", "Server shutting down"))
            self.destroy()
        elif cmd == "game_start":
            info = msg
            username = self.get_current_user()
            game_dir = Path(__file__).parent / "players" / username / "games" / f"{info.get("game_id")}_{info.get("game_name")}" / f"v{info.get("game_version")}"
            print("game dir exists? ", game_dir.exists())
            if game_dir.exists():

                print("game dir is ",game_dir)
                messagebox.showinfo("Start Game", "Game has started")
                proc = subprocess.Popen([sys.executable, "-m", "client.client", "--host", info["game_host"], "--port", str(info["game_port"]), "--room", str(info["room_id"]), "--user", str(username)], cwd=game_dir)
                self.withdraw()
                proc.wait()
                self.after(0, self.deiconify)

                if info["host_name"] == self.get_current_user():
                    resp = self.lobby_client.send_request({
                        "cmd": "finish_game",
                        "room_id": info["room_id"],    
                    })
                # print("finish game", resp)
                self.show_frame("PlayerHomeFrame")

            else:
                print("game dir is ",game_dir)
                messagebox.showerror("Start Game", "Game started failed")

        else:
            print("[event]", msg)

    def handle_room_update(self, msg: dict):
        room_id = msg.get("room_id")
        players = msg.get("players", [])

        room = self.get_current_room()
        if not room:
            return
        if room.get("room_id") != room_id:
            return
        
        room["players"] = players
        self.set_current_room(room)

        frame = self.frames.get("RoomWaitFrame")
        if frame is not None:
            frame.render_players_from_current_room()
    def handle_room_closed(self, msg):
        room_id = msg.get("room_id")
        room = self.get_current_room()
        if not room:
            return
        if room.get("room_id") != room_id:
            return

        self.set_current_room(None)
        self.set_status("Room closed")
        message = msg.get("message", f"Room #{room_id} has been closed")
        from tkinter import messagebox
        messagebox.showinfo("Room closed", message)
        self.show_frame("PlayerHomeFrame")


def run_app():
    host, port = load_connection_info()
    client = LobbyClient(host=host, port=port)
    app = PlayerClientApp(client)
    app.mainloop()


if __name__ == "__main__":
    run_app()
