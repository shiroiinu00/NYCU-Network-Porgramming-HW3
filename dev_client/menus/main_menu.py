import tkinter as tk

class MainMenuFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        content = tk.Frame(self, bg=self.controller.bg_color)
        content.pack(expand=True)

        

        tk.Label(content, text="Developer Client", font=("Arial", 16, "bold"), bg=self.controller.bg_color, fg=self.controller.fg_color).pack(pady=20)

        tk.Button(
            content, text="Login", width=12, bg="gray30", fg=self.controller.fg_color,
            command=lambda: controller.show_frame("LoginFrame")
        ).pack(pady=5)

        tk.Button(
            content, text="Register", width=12, bg="gray30", fg=self.controller.fg_color,
            command=lambda: controller.show_frame("RegisterFrame")
        ).pack(pady=5)