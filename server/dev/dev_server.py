import socket
import threading
import json
import os
import signal
import zipfile
from pathlib import Path

PORT = None
HOST = None

running = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_STORE_ROOT = os.path.join(BASE_DIR, "game")


def load_connection_info():
    _config_path = Path(__file__).parent / "config.json"

    with _config_path.open("r", encoding="utf-8") as f:
        _cfg = json.load(f)
    global PORT, HOST
    HOST = str(_cfg["HOST"])
    PORT = int(_cfg["PORT"])

    print(f"Host: {HOST}/ {type(HOST)}, Port: {PORT} / {type(PORT)}")

def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("connection closed while receiving file")
        buf += chunk
    return buf


def handle_client(conn, addr):
    print(f"[file] connected from {addr}")
    f = conn.makefile("rb")

    try:
        # read header
        header_line = f.readline()
        if not header_line:
            print("[file] empty header")
            return
        
        header = json.loads(header_line.decode("utf-8"))
        action = header.get("action") or "upload"

        if action == "download":
            download_path = header.get("download_path")
            if not download_path:
                resp = {
                    "ok": False,
                    "error": "BAD_HEADER",
                    "message": "download_path missing"
                }
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                return
            full_path = os.path.join(GAME_STORE_ROOT, download_path)
            if not os.path.isfile(full_path):
                resp = {
                    "ok": False,
                    "error": "BAD_PATH",
                    "message": "download_path is wrong"
                }
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                return
            file_size = os.path.getsize(full_path)
            conn.sendall((json.dumps({
                "ok": True,
                "file_size": file_size
            }) + "\n").encode("utf-8"))
            with open(full_path, "rb") as rf:
                while True:
                    chunk = rf.read(65536)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            return
        else:
            upload_path = header.get("upload_path")
            file_size = header.get("file_size")
            version = header.get("version")
            if not upload_path or not isinstance(file_size, int):
                resp = {
                    "ok": False,
                    "error": "BAD_HEADER",
                    "message": "upload_path/file_size missing"
                }
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                return
            
            full_path = os.path.join(GAME_STORE_ROOT, upload_path)
            full_dir = os.path.dirname(full_path)
            os.makedirs(full_dir, exist_ok=True)

            ack = {
                "ok": True,
                "message": "ready"
            }
            conn.sendall((json.dumps(ack) + "\n").encode("utf-8"))

            # receive binary
            remaining = file_size
            with open(full_path, "wb") as out:
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    chunk = conn.recv(chunk_size)
                    if not chunk:
                        raise RuntimeError("connection closed mid-file")
                    out.write(chunk)
                    remaining -= len(chunk)
            print(f"[file] saved {file_size} bytes to {full_path}")

            # extract
            if full_path.lower().endswith(".zip"):
                extract_dir = Path(full_dir) / f"v{version}"
                extract_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(full_path, "r") as zf:
                    zf.extractall(extract_dir)
                # zip_path = str(extract_dir) + ".zip"
                # print(f"zip_path: {zip_path}")
                # try:
                #     os.remove(zip_path)
                # except FileNotFoundError:
                #     print("[FILE] not found the file")
                #     pass

            done = {
                "ok": True,
                "message": "upload complete",
                "store_path": full_path,
            }
            conn.sendall((json.dumps(done) + "\n").encode("utf-8"))
    except Exception as e:
        print("[file] error", e)
        try:
            resp = {
                "ok": False,
                "error": "SERVER_ERROR",
                "message": str(e),
            }
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        except Exception:
            pass
    finally:
        f.close()
        conn.close()
        print(f"[file] connection closed from {addr}")


def handle_shutdown(signum, frame):
    global running
    print("\nShutdown signal received!\n")
    running = False

def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    load_connection_info()
    os.makedirs(GAME_STORE_ROOT, exist_ok=True)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(0.5)
    global running
    running = True
    print(f"[file] listening on {HOST}:{PORT}, base={GAME_STORE_ROOT}")
    try:
        while running:
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nCtrl+C pressed, shutting down...")
    finally:
        server.close()
        print("Server closed.")




if __name__ == "__main__":
    main()