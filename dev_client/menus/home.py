import tkinter as tk
from tkinter import messagebox


class DeveloperHomeFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        outer = tk.Frame(self, bg=self.controller.bg_color)
        outer.pack(expand=True)

        self.label_welcome = tk.Label(outer, text="Welcome,", font=("Arial", 14, "bold"), bg=self.controller.bg_color, fg=self.controller.fg_color,)
        self.label_welcome.pack(pady=(20, 5))

        self.label_username = tk.Label(outer, text="<username>", font=("Arial", 12), bg=self.controller.bg_color, fg=self.controller.fg_color,)
        self.label_username.pack(pady=(0, 15))

        btn_frame = tk.Frame(outer , bg=self.controller.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="View Game Library", width=15, bg="gray30", fg=self.controller.fg_color,
            command=self.on_view_game_library
        ).grid(row=0, column=0, padx=5, pady=3)

        # tk.Button(
        #     btn_frame, text="Update Version", width=15,
        #     command=self.on_browse_games
        # ).grid(row=1, column=0, padx=15, pady=3)

        tk.Button(
            btn_frame, text="Upload Game", width=15, bg="gray30", fg=self.controller.fg_color,
            command=self.on_upload_games
        ).grid(row=2, column=0, padx=15, pady=3)

        tk.Button(
            btn_frame, text="Logout", width=15, bg="gray30", fg=self.controller.fg_color,
            command=self.on_logout
        ).grid(row=3, column=0, padx=5, pady=(10, 3))
        
        


    def on_show(self):
        username = self.controller.get_current_user() or "<unknown>"
        self.controller.set_status(f" ")
        self.label_username.config(text=username)

    def on_view_game_library(self):
        self.controller.show_frame("GameLibraryFrame")

    def on_browse_games(self):
        self.controller.show_frame("DevUploadFrame")

    def on_upload_games(self):
        self.controller.show_frame("CreateGameFrame")

    def on_logout(self):
        self.controller.set_current_user(None)
        self.controller.set_status("Logged out")
        messagebox.showinfo("Logout", "You have been logged out.")
        self.controller.show_frame("MainMenuFrame")
