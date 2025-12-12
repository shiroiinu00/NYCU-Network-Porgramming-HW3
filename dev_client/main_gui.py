import tkinter as tk
import json
from tkinter import messagebox

from .api_client import load_connection_info, LobbyClient

from .menus.main_menu import MainMenuFrame
from .menus.auth import RegisterFrame, LoginFrame
from .menus.home import DeveloperHomeFrame
from .menus.game_library import GameLibraryFrame
from .menus.upload_version import DevUploadFrame
from .menus.create_game import CreateGameFrame

class PlayerClientApp(tk.Tk):
    def __init__(self, client: LobbyClient):
        super().__init__()

        self.title("HW3 Developer Client")
        self.resizable(False, False)
        self.bg_color = 'gray8'
        self.fg_color = 'white'

        self.lobby_client = client
        self.lobby_client.on_event = self._on_server_event

        self.status_var = tk.StringVar(value="")
        self.current_user: str | None = None
        self.current_room: dict | None = None
        self.select_game_id: int | None = None
        self.select_game_name: str | None = None
        

        container = tk.Frame(self, bg=self.bg_color)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        status_label = tk.Label(self, textvariable=self.status_var, fg="white", bg="gray8")
        status_label.pack(side="bottom", pady=4)

        self.frames = {}
        for F in (MainMenuFrame, RegisterFrame, LoginFrame, DeveloperHomeFrame, GameLibraryFrame, DevUploadFrame, CreateGameFrame):
            frame = F(parent=container, controller=self)
            frame.configure(bg=self.bg_color)
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
        self.configure(bg=self.bg_color)

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
        elif cmd == "server_shutdown":
            messagebox.showinfo("Server", msg.get("message", "Server shutting down"))
            self.destroy()

        else:
            print("[event]", msg)


def run_app():
    host, port = load_connection_info()
    client = LobbyClient(host=host, port=port)
    app = PlayerClientApp(client)
    app.mainloop()


if __name__ == "__main__":
    run_app()
