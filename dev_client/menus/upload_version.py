import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from ..api_client import upload_file_to_server
import shutil
import zipfile


class DevUploadFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Upload New Version", font=("Arial", 14, "bold"), bg=self.controller.bg_color, fg=self.controller.fg_color,).pack(pady=10)

        # --- Select game ---
        self.game_label = tk.Label(self, text="", bg=self.controller.bg_color, fg=self.controller.fg_color,)
        self.game_label.pack(pady=10)
        self.game_var = tk.StringVar()
        # self.game_dropdown = tk.OptionMenu(self, self.game_var, ())
        # self.game_dropdown.pack(pady=5)

        # --- Version ---
        tk.Label(self, text="Version (e.g., 1.0.0):", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_version = tk.Entry(self, width=30)
        self.entry_version.pack(pady=5)

        # --- Changelog ---
        tk.Label(self, text="Changelog:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.text_changelog = tk.Text(self, width=40, height=5)
        self.text_changelog.pack(pady=5)

        # --- Source path selection ---
        tk.Label(self, text="Select Local Folder / File to Upload:", bg=self.controller.bg_color, fg=self.controller.fg_color,).pack()
        self.entry_source_var = tk.StringVar()
        self.entry_source = tk.Entry(self, width=40, textvariable=self.entry_source_var, state="readonly")
        self.entry_source.pack(pady=5)
        tk.Button(self, text="Browse", bg="gray30", fg=self.controller.fg_color, command=self.browse_source).pack()

        # --- Buttons ---
        btn_frame = tk.Frame(self, bg=self.controller.bg_color)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Upload", width=12, bg="gray30", fg=self.controller.fg_color, command=self.upload).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Back", width=12, bg="gray30", fg=self.controller.fg_color,
                  command=lambda: controller.show_frame("GameLibraryFrame")).grid(row=0, column=1, padx=5)

        # Game list cache
        self.dev_games = []


    def on_show(self):
        try:
            resp = self.controller.lobby_client.send_request({"cmd": "developer_list_games",})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            messagebox.showerror("Error", resp.get("message"))
            return

        self.dev_games = resp["games"]

        # # 更新 dropdown
        # menu = self.game_dropdown["menu"]
        # menu.delete(0, "end")

        # for g in self.dev_games:
        #     label = f"{g['game_id']} - {g['game_name']}"
        #     menu.add_command(label=label, command=lambda value=label: self.game_var.set(value))

        # if self.dev_games:
        self.game_label.config(
            text=f"Game\n{self.controller.select_game_id} - {self.controller.select_game_name}"
        )
        first_label = f"{self.controller.select_game_id} - {self.controller.select_game_name}"
        self.game_var.set(first_label)


    def browse_source(self):
        path = filedialog.askdirectory(title="Select Folder to Upload")
        if not path:
            return
        self.entry_source_var.set(path)

    def upload(self):
        game_label = self.game_var.get()
        version = self.entry_version.get().strip()
        changelog = self.text_changelog.get("1.0", tk.END).strip()
        src_path = self.entry_source.get().strip()

        if not (game_label and version and src_path):
            messagebox.showwarning("Missing Data", "Please fill all fields.")
            return

        try:
            game_id = int(game_label.split("-")[0].strip())
        except:
            messagebox.showerror("Error", "Invalid game selection.")
            return

        game = next(g for g in self.dev_games if g["game_id"]  ==  game_id)
        game_name = game.get("game_name")
        game_version = game.get("latest_version")

        check_result = self.controller.lobby_client.check_upload_version_valid(version, game_version)
        if check_result == -1 :
            messagebox.showerror("Upload Failed", "Please enter valid version number")
            return
        if check_result == -2 :
            messagebox.showerror("Upload Failed", f"The valid version number should higher the latest version number (latest: {game_version})")
            return
        # game_name = next(g["game_name"] for g in self.dev_games if g["game_id"] == game_id)

        dev = self.controller.get_current_user()
        workspace = Path("dev_client/dev_workspace") / dev / f"{game_id}_{game_name}" / f"v{version}"
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

        try:
            resp = self.controller.lobby_client.send_request({
                "cmd": "developer_create_version",
                "game_id": game_id,
                "game_version": version,
                "changelog": changelog,
            })
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            messagebox.showerror("Upload Failed", resp.get("message"))
            return

        upload_path = resp.get("upload_path")
        if not upload_path:
            messagebox.showerror("Upload Failed", "server did not return upload_path")
            return
        
        try:
            result = upload_file_to_server(zip_path, upload_path, version)
        except Exception as e:
            messagebox.showerror("File Upload Failed". str(e))
            self.controller.set_status(f"File upload")
            return
        
        messagebox.showinfo(
            "Upload Done",
            f"Metadata + file upload success.\n"
            f"Zip: {zip_path}\n"
            f"Server: {result.get('stored_path', upload_path)}"
        )

        self.controller.set_status(f"Uploaded version {version}")
        self.controller.show_frame("DeveloperHomeFrame")
