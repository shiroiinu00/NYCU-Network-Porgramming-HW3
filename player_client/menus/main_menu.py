import tkinter as tk

class MainMenuFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        content = tk.Frame(self)
        content.pack(expand=True)

        

        tk.Label(content, text="Player Client", font=("Arial", 16, "bold")).pack(pady=20)

        tk.Button(
            content, text="Login", width=12,
            command=lambda: controller.show_frame("LoginFrame")
        ).pack(pady=5)

        tk.Button(
            content, text="Register", width=12,
            command=lambda: controller.show_frame("RegisterFrame")
        ).pack(pady=5)