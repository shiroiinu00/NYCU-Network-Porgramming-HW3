import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import shutil
import zipfile
from ..api_client import upload_file_to_server


class CreateGameFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Create New Game", font=("Arial", 16, "bold"), bg=self.controller.bg_color, fg=self.controller.fg_color,).pack(pady=20)

        # Game name
        tk.Label(self, text="Game Name:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_name = tk.Entry(self, width=30)
        self.entry_name.pack(pady=5)

        # Description
        tk.Label(self, text="Description:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.text_desc = tk.Text(self, width=30, height=5)
        self.text_desc.pack(pady=5)

        # Max players
        tk.Label(self, text="Max Players:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_max_players = tk.Entry(self, width=10)
        self.entry_max_players.pack(pady=5)

        # Version info
        tk.Label(self, text="Version (e.g., 1.0.0):", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_version = tk.Entry(self, width=20)
        self.entry_version.pack(pady=5)

        tk.Label(self, text="Changelog:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.text_changelog = tk.Text(self, width=30, height=4)
        self.text_changelog.pack(pady=5)

        tk.Label(self, text="Select game folder to upload:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_source_var = tk.StringVar()
        self.entry_source = tk.Entry(self, width=40, textvariable=self.entry_source_var, state="readonly")
        self.entry_source.pack(pady=5)
        tk.Button(self, text="Browse", bg="gray30", fg=self.controller.fg_color, command=self.browse_source).pack(pady=2)

        # Buttons
        btn_frame = tk.Frame(self, bg=self.controller.bg_color)
        btn_frame.pack(pady=5)

        tk.Button(
            btn_frame, text="Create", width=12, bg="gray30", fg=self.controller.fg_color,
            command=self.on_create
        ).pack(pady=5)

        tk.Button(
            btn_frame, text="Back", width=12, bg="gray30", fg=self.controller.fg_color,
            command=lambda: controller.show_frame("DeveloperHomeFrame")
        ).pack(pady=5)

    def on_show(self):
        self.entry_name.delete(0, tk.END)
        self.text_desc.delete("1.0", tk.END)
        self.entry_max_players.delete(0, tk.END)
        self.entry_version.delete(0, tk.END)
        self.text_changelog.delete("1.0", tk.END)
        self.entry_source_var.set("")

    def browse_source(self):
        path = filedialog.askdirectory(title="Select Folder to Upload")
        if path:
            self.entry_source_var.set(path)

    def on_create(self):
        name = self.entry_name.get().strip()
        desc = self.text_desc.get("1.0", tk.END).strip()
        max_players_str = self.entry_max_players.get().strip()
        version = self.entry_version.get().strip()
        changelog = self.text_changelog.get("1.0", tk.END).strip()
        src_path = self.entry_source_var.get().strip()

        if not name:
            messagebox.showwarning("Input error", "Game name is required.")
            return
        if not version:
            messagebox.showwarning("Input error", "Version is required.")
            return
        if not src_path:
            messagebox.showwarning("Input error", "Please select a folder to upload.")
            return

        max_players = None
        if max_players_str:
            try:
                max_players = int(max_players_str)
            except ValueError:
                messagebox.showwarning("Input error", "Max players must be an integer.")
                return

        req = {
            "cmd": "developer_create_game",
            "game_name": name,
            "game_description": desc,
            "max_players": max_players,
        }

        try:
            resp = self.controller.lobby_client.send_request(req)
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            msg = resp.get("message", "Failed to create game.")
            messagebox.showerror("Create game failed", f"{msg}\n(code: {resp.get('error')})")
            self.controller.set_status(f"Create game FAIL: {msg}")
            return

        game_id = resp.get("game_id")
        self.controller.set_status(f"Game created: {name} (id={game_id})")
        dev = self.controller.get_current_user()

        # prepare workspace
        workspace = Path("dev_client/dev_workspace") / dev / f"{game_id}_{name}" / f"v{version}"
        workspace.mkdir(parents=True, exist_ok=True)

        src = Path(src_path)
        if src.is_dir():
            shutil.copytree(src, workspace, dirs_exist_ok=True)
        else:
            shutil.copy2(src, workspace)

        zip_path = workspace.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for file in workspace.rglob("*"):
                rel_path = file.relative_to(workspace)
                z.write(file, rel_path)

        # create version metadata
        try:
            ver_resp = self.controller.lobby_client.send_request({
                "cmd": "developer_create_version",
                "game_id": game_id,
                "game_version": version,
                "changelog": changelog,
            })
        except Exception as e:
            messagebox.showerror("Network error", f"Create version failed: {e}")
            return

        if not ver_resp.get("ok"):
            msg = ver_resp.get("message", "Failed to create version.")
            messagebox.showerror("Create version failed", f"{msg}\n(code: {ver_resp.get('error')})")
            return

        upload_path = ver_resp.get("upload_path")
        if not upload_path:
            messagebox.showerror("Upload failed", "Server did not return upload_path")
            return

        try:
            result = upload_file_to_server(zip_path, upload_path, version)
        except Exception as e:
            messagebox.showerror("File upload failed", str(e))
            self.controller.set_status("File upload failed")
            return

        messagebox.showinfo(
            "Game created & uploaded",
            f"Game created.\nID: {game_id}\nName: {name}\n"
            f"Version: {version}\nZip: {zip_path}\nServer: {result.get('stored_path', upload_path)}"
        )

        self.controller.set_status(f"Uploaded {name} v{version}")
        # 建完之後回到 DevHome
        self.controller.show_frame("DeveloperHomeFrame")
