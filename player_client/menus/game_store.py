import tkinter as tk
import json, zipfile, shutil, os
from tkinter import messagebox
from pathlib import Path

from ..api_client import get_user_games, download_file_from_server, cmp_ver, PLAYERS_DIR


class GameStoreFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Game Store", font=("Arial", 14, "bold")).pack(pady=10)

        self.listbox = tk.Listbox(self, width=70, height=10)
        self.listbox.pack(padx=10, pady=5)

        self.info_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.info_var, fg="gray").pack(pady=(0, 5))

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Refresh", width=10,
            command=self.on_refresh
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame, text="View Detail / Rating", width=15,
            command=self.on_view_detail
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            btn_frame, text="Download / Update", width=15,
            command=self.on_download
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            btn_frame, text="Back", width=10,
            command=lambda: controller.show_frame("PlayerHomeFrame")
        ).grid(row=0, column=3, padx=5)

        self.current_games: list[dict] = []

    def on_show(self):
        self.on_refresh()

    def on_refresh(self):
        username = self.controller.get_current_user()
        if not username:
            self.info_var.set("Not logged in.")
            self.listbox.delete(0, tk.END)
            return

        # 1. 先拿本地已安裝遊戲
        local_games = {g["game_id"]: g for g in get_user_games(username)}

        # 2. 向 server 拿所有 active 遊戲 + 最新版本
        try:
            resp = self.controller.lobby_client.send_request({"cmd": "list_games"})
        except Exception as e:
            messagebox.showerror("Network error", str(e))
            return

        if not resp.get("ok"):
            msg = resp.get("message", "Failed to list games.")
            self.info_var.set(msg)
            messagebox.showerror("List games", f"{msg})")
            return

        games = resp.get("games", [])
        self.current_games = games

        self.listbox.delete(0, tk.END)
        if not games:
            self.info_var.set("No games on server.")
            return

        for g in games:
            gid = g["game_id"]
            name = g.get("game_name", f"Game {gid}")
            latest_ver = g.get("latest_version") or "N/A"
            local = local_games.get(gid)
            print(local)

            if local is None:
                local_ver = "-"
            else:
                local_ver = local.get("version", "0.0.0")
            
            if cmp_ver(local_ver, latest_ver) < 0 and local_ver != '-':
                status = f"Installed v{local_ver}, update available (latest {latest_ver})"    
            elif local_ver == '-':
                status = "Not installed"
            else:
                status = f"Installed v{local_ver}"

            line = f"[{gid}] {name} | latest: {latest_ver} | {status}"
            self.listbox.insert(tk.END, line)

        self.info_var.set(f"{len(games)} game(s) on server.")

    def _get_selected_game(self):
        idxs = self.listbox.curselection()
        if not idxs:
            return None
        idx = idxs[0]
        if idx < 0 or idx >= len(self.current_games):
            return None
        return self.current_games[idx]

    def on_download(self):
        g = self._get_selected_game()
        if not g:
            messagebox.showwarning("Select game", "Please select a game first.")
            return
        
        username = self.controller.get_current_user()
        gid = g["game_id"]
        name = g.get("game_name", f"Game {gid}")
        latest_ver = g.get("latest_version")
        latest_ver_id = g.get("latest_version_id")
        upload_path = g.get("upload_path")

        check_result = self.controller.lobby_client.check_vlocal_higher_vstore(username, gid)
        if  check_result == 1:
            messagebox.showinfo("Download", "You have installed the latest version")
            return
        # elif check_result == -1:
        #     messagebox.showinfo("Download", "You don't have the game. Please install first")
        #     return


        if latest_ver is None or latest_ver_id is None:
            messagebox.showwarning("No version", "This game has no uploaded version yet.")
            return

        dest_dir = PLAYERS_DIR / username / "games" / f"{gid}_{name}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_zip = dest_dir / f"v{latest_ver}.zip"
        try:
            download_file_from_server(upload_path, dest_zip)
        except Exception as e:
            messagebox.showerror("Download failed", str(e))
            self.controller.set_status("Download failed")
            return
        
        # do unzip
        extracted_dir = dest_dir / f"v{latest_ver}"
        try:
            with zipfile.ZipFile(dest_zip, "r") as zf:
                extracted_dir.mkdir(parents=True, exist_ok=True)
                zf.extractall(extracted_dir)
        except Exception as e:
            messagebox.showwarning("Unzip failed", f"File saved as {dest_zip}, but unzip fialed: {e}")
        
        try:
            server_path = extracted_dir / "server"
            shutil.rmtree(server_path)            
        except FileNotFoundError:
            pass

        try:
            os.remove(dest_zip)
        except FileNotFoundError:
            pass
         
        
        meta = {
            "game_id": gid,
            "name": name,
            "version": latest_ver,
        }
        (dest_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self.controller.set_status(f"Downloaded {name} v{latest_ver}")
        messagebox.showinfo("Download", "Download successfully")
        self.on_refresh()
    def on_view_detail(self):
        g = self._get_selected_game()
        if not g:
            messagebox.showwarning("Select game", "Please select a game first")
            return
        self.controller.selected_game_id = g["game_id"]
        self.controller.selected_game_name = g.get("game_name")
        self.controller.show_frame("GameDetailFrame")
    


