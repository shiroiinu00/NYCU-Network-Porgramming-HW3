import tkinter as tk
from tkinter import messagebox

class RegisterFrame(tk.Frame):
    def __init__(self, parent, controller,):
        super().__init__(parent)
        self.controller = controller
        self.client = self.controller.lobby_client

        # 只有這一層用 pack
        outer = tk.Frame(self)
        outer.pack(expand=True)

        tk.Label(outer, text="Register", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=10
        )

        tk.Label(outer, text="Username:").grid(
            row=1, column=0, sticky="e", padx=10, pady=5
        )
        self.entry_username = tk.Entry(outer, width=22)
        self.entry_username.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(outer, text="Password:").grid(
            row=2, column=0, sticky="e", padx=10, pady=5
        )
        self.entry_password = tk.Entry(outer, width=22, show="*")
        self.entry_password.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(outer, text="Display name:").grid(
            row=3, column=0, sticky="e", padx=10, pady=5
        )
        self.entry_display = tk.Entry(outer, width=22)
        self.entry_display.grid(row=3, column=1, padx=10, pady=5)

        self.show_pw_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            outer,
            text="Show password",
            variable=self.show_pw_var,
            command=self.toggle_password,
        ).grid(row=4, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(outer)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=12)

        tk.Button(btn_frame, text="Submit", width=10,
                  command=self.on_submit).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Back", width=10,
                  command=self.go_back
                  ).grid(row=0, column=1, padx=5)
        
    def on_show(self):
        self.entry_username.delete(0, tk.END)
        self.entry_password.delete(0, tk.END)

    def on_submit(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get()
        display_name = self.entry_display.get().strip() or username

        if not username or not password:
            messagebox.showwarning("Input error", "Username and password are required.")
            return

        try:
            resp = self.client.register_player(username, password, display_name)
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if resp.get("ok"):
            msg = resp.get("message", "Register success.")
            self.controller.set_status(f"Register OK: {msg}")
            messagebox.showinfo("Register", msg)
            self.controller.show_frame("MainMenuFrame")
        else:
            msg = resp.get("message", "Register failed.")
            self.controller.set_status(f"Register FAIL: {msg}")
            messagebox.showerror("Register failed", f"{msg}")

    def toggle_password(self):
        if self.show_pw_var.get():
            self.entry_password.config(show="")
        else:
            self.entry_password.config(show="*")
    def go_back(self):
        self.controller.set_status("")
        self.controller.show_frame("MainMenuFrame")


class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.client = self.controller.lobby_client

        outer = tk.Frame(self)
        outer.pack(expand=True)

        tk.Label(outer, text="Login", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=10
        )

        tk.Label(outer, text="Username:").grid(
            row=1, column=0, sticky="e", padx=10, pady=5
        )
        self.entry_username = tk.Entry(outer, width=22)
        self.entry_username.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(outer, text="Password:").grid(
            row=2, column=0, sticky="e", padx=10, pady=5
        )
        self.entry_password = tk.Entry(outer, width=22, show="*")
        self.entry_password.grid(row=2, column=1, padx=10, pady=5)

        self.show_pw_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            outer,
            text="Show password",
            variable=self.show_pw_var,
            command=self.toggle_password,
        ).grid(row=3, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(outer)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=12)

        tk.Button(btn_frame, text="Login", width=10,
                  command=self.on_login).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Back", width=10,
                  command=self.go_back
                  ).grid(row=0, column=1, padx=5)
    
    def on_show(self):
        self.entry_username.delete(0, tk.END)
        self.entry_password.delete(0, tk.END)

    def on_login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get()

        if not username or not password:
            messagebox.showwarning("Input error", "Username and password are required.")
            return

        try:
            resp = self.client.login_player(username, password)
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if resp.get("ok"):
            msg = resp.get("message", "Login success.")
            self.controller.set_status(f"Login OK: {msg}")
            self.controller.set_current_user(username)
            messagebox.showinfo("Login", msg)
            self.controller.show_frame("PlayerHomeFrame")
        else:
            msg = resp.get("message", "Login failed.")
            self.controller.set_status(f"Login FAIL: {msg}")
            messagebox.showerror("Login failed", f"{msg}")

    def toggle_password(self):
        if self.show_pw_var.get():
            self.entry_password.config(show="")
        else:
            self.entry_password.config(show="*")
    def go_back(self):
        self.controller.set_status("")
        self.controller.show_frame("MainMenuFrame")
