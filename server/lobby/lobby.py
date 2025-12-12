import json
import socket
import threading
import time
import signal
import subprocess, sys
from pathlib import Path

from typing import Dict
from server.db import accounts_repo, room_repo , gamelog_repo, games_repo, ratings_repo, init_db
from server.common.protocol import send_json, recv_json

HOST = "0.0.0.0"
PORT = 10050

running = True

online_players: Dict[str, socket.socket] = {}
sock_usernames: Dict[socket.socket, str] = {}

online_developers: Dict[str, socket.socket] = {}
sock_devnames: Dict[socket.socket, str] = {}

room_members: Dict[int, set[str]] = {}
room_states: Dict[int, dict] = {}
user_room: Dict[str, int] = {}

game_processes: dict[int, subprocess.Popen] = {}


def load_connection_info():
    _config_path = Path(__file__).parent / "config.json"

    with _config_path.open("r", encoding="utf-8") as f:
        _cfg = json.load(f)
    global PORT, HOST
    HOST = str(_cfg["SERVER_HOST"])
    PORT = int(_cfg["SERVER_PORT"])

    print(f"Host: {HOST}/ {type(HOST)}, Port: {PORT} / {type(PORT)}")

def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]

def handle_player_register(request: dict) -> dict:
    username = request.get("username", "").strip()
    password = request.get("password", "")
    display_name = request.get("display_name") or username

    if not username or not password:
        return {
            "ok": False,
            "cmd": "player_register",
            "error": "BAD_INPUT",
            "message": "username and password are required"
        }

    try:
        accounts_repo.create_player(username, password, display_name)
    except ValueError as e:
        if str(e) == "USERNAME_TAKEN":
            return {
                "ok": False,
                "cmd": "player_register",
                "error": "USERNAME_TAKEN",
                "message": "username already taken"
            }
        else:
            return {
                "ok": False,
                "cmd": "player_register",
                "error": "INTERNAL",
                "message": "internal error"
            }
    print(f"[*] User {username} registered success.")
    return {
        "ok": True,
        "cmd": "player_register",
        "message": "register success"
    }

def handle_player_login(request: dict, session: socket.socket) -> dict:
    username = request.get("username", "").strip()
    password = request.get("password", "")

    if not accounts_repo.verify_player_password(username, password):
        return {
            "ok": False,
            "cmd": "player_login",
            "error": "INVALID_CREDENTIALS",
            "message": "invalid username or password"
        }
    
    old_session = online_players.get(username)
    if old_session is not None and old_session is not session:
        try:
            send_json(old_session, {
                "ok": False,
                "cmd": "force_logout",
                "message": "logged in from another location",
            })
        except Exception:
            pass
        try:
            old_session.close()
        except Exception:
            pass

    # remember connection info
    online_players[username] = session
    sock_usernames[session] = username

    print(f"[*] User {username} logined success.")
    return {
        "ok": True, 
        "cmd": "player_login",
        "message": "login success"
    }

def handle_room_create(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "create_room",
            "error": "NOT_LOGGED_IN",
            "message": "login required"
        }
    
    game_id = request.get("game_id")
    game = games_repo.get_game_by_id(game_id)
    max_players = game.get("max_players")
    try:
        game_id = int(game_id)
        max_players = int(max_players)
    except(TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "create_room",
            "error": "BAD_INPUT",
            "message": "game_id and max_players must be intergers"
        }
    
    if max_players <=0:
        return {
            "ok": False,
            "cmd": "create_room",
            "error": "BAD_INPUT",
            "message": "max_players must be > 0"
        }
    
    game_status = game.get("game_status")
    if game_status != 'active':
        return {
            "ok": False,
            "cmd": "create_room",
            "error": "GAME_IS_NOT_ACTIVE",
            "message": "Owner of the game deleted this game. You cannot create the room."
        }
    
    player_row = accounts_repo.get_player_by_username(username)
    if player_row is None:
        return {
            "ok": False,
            "cmd": "create_room",
            "error": "NO_SUCH_PLAYER",
            "message": "player not found"
        }
    
    host_player_id = player_row["id"]

    room_id = room_repo.create_room(host_player_id, game_id, max_players)

    if room_id not in room_members:
        room_members[room_id] = set()
    room_members[room_id].add(username)

    game_name = game.get("game_name")

    room_states[room_id] = {
        "room_id": room_id,
        "host": username,
        "game_id": game_id,
        "game_name": game_name,
        "max_players": max_players,
        "status": "open",
    }

    user_room[username] = room_id
    print(f"max_players {max_players}")
    return {
        "ok": True,
        "cmd": "create_room",
        "room_id": room_id,
        "game_id": game_id,
        "max_players": max_players,
        "message": "room created",
    }

def handle_join_room(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "join_room",
            "error": "NOT_LOGGED_IN",
            "message": "login required"
        }
    
    room_id_row = request.get("room_id")
    try:
        room_id = int(room_id_row)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "join_room",
            "error": "BAD_INPUT",
            "message": "room_id must be integer",
        }
    room = room_repo.get_room(room_id)
    members = room_members.get(room_id)
    if members is None:
        return {
            "ok": False,
            "cmd": "join_room",
            "error": "NO_SUCH_ROOM",
            "message": f"room {room_id} not found",
        }
    
    # if username in members:
    #     return {
    #         "ok": True,
    #         "cmd": "join_room",
    #         "room_id": room_id,
    #         "message": "already in room",
    #     }
    
    members.add(username)
    if len(members) > (room.get("max_players")):
        return {
            "ok": False,
            "cmd": "join_room",
            "error": "ROOM_FULL",
            "message": f"room {room_id} is full. Please join others room",
        }
    user_room[username] = room_id
    # broadcast join message
    player_list = list(members)
    evt = {
        "cmd": "room_update",
        "room_id": room_id,
        "players": player_list,
    }
    for name in player_list:
        members_sock = online_players.get(name)
        if members_sock is not None and sock != members_sock:
            send_json(members_sock, evt)
    return{
        "ok": True,
        "cmd": "join_room",
        "room_id": room_id,
        "message": "joined room",
        "players": player_list
    }

def handle_room_info(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "room_info",
            "error": "NOT_LOGGED_IN",
            "message": "login required",
        }
    
    room_id_raw = request.get("room_id")
    try:
        room_id = int(room_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "room_info",
            "error": "BAD_INPUT",
            "message": "room_id must be integer",
        }

    members = room_members.get(room_id)
    if members is None:
        return {
            "ok": False,
            "cmd": "room_info",
            "error": "NO_SUCH_ROOM",
            "message": f"room {room_id} not found",
        }

    return {
        "ok": True,
        "cmd": "room_info",
        "room_id": room_id,
        "players": list(members),
    }

def handle_list_room(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "list_rooms",
            "error": "NOT_LOGGED_IN",
            "message": "login required",
        }
    
    rooms_list = []
    for room_id, state in room_states.items():
        if state.get("status") != "open":
            continue
        members = room_members.get(room_id, set())
        rooms_list.append({
            "room_id": room_id,
            "host": state.get("host"),
            "game_name": state.get("game_name"),
            "game_id": state.get("game_id"),
            "current_players": len(members),
            "max_players": state.get("max_players"),
            "status": state.get("status"),
        })
    return {
        "ok": True,
        "cmd": "list_rooms",
        "rooms": rooms_list,
    }

def handle_leave_room(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "leave_room",
            "error": "NOT_LOGGED_IN",
            "message": "login required",
        }
    
    room_id = user_room.get(username)
    if room_id is None:
        return {
            "ok": False,
            "cmd": "leave_room",
            "error": "NOT_IN_ROOM",
            "message": "you are not in any room",
        }
    members = room_members.get(room_id)
    state = room_states.get(room_id)
    if members is None or state is None:
        user_room.pop(username, None)
        return{
            "ok": True,
            "cmd": "leave_room",
            "room_id": room_id,
            "message": "left room"
        }
    members.discard(username)
    user_room.pop(username, None)

    host = state.get("host")

    if username == host:
        state["status"] = "closed"
        evt = {
            "cmd": "room_closed",
            "room_id": room_id,
            "message": f"host {host} left, room closed",
        }

        for name in list(members):
            sock2 = online_players.get(name)
            if sock2 is not None:
                send_json(sock2, evt)
        
        room_members.pop(room_id, None)
        room_states.pop(room_id, None)
        room_repo.delete_room(room_id)
        return {
            "ok": True,
            "cmd": "leave_room",
            "room_id": room_id,
            "message": "left room as host, room closed",
        }
    else:
        evt = {
            "cmd": "room_update",
            "room_id": room_id,
            "players": list(members)
        }

        for name in list(members):
            sock2 = online_players.get(name)
            if sock2 is not None:
                send_json(sock2, evt)
            
        return {
            "ok": True,
            "cmd": "leave_room",
            "room_id": room_id,
            "message": "left room"
        }

def handle_list_games(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    devname = sock_devnames.get(sock)
    if not username and not devname:
        return {
            "ok": False,
            "cmd": "list_games",
            "error": "NOT_LOGGED_IN",
            "message": "login required",
        }
    
    games = gamelog_repo.list_games_with_latest_version()

    return {
        "ok": True,
        "cmd": "list_games",
        "games": games
    }

def handle_developer_register(request: dict) -> dict:
    username = request.get("username").strip()
    password = request.get("password")
    display_name = request.get("display_name") or username

    if not username or not password:
        return {
            "ok": False,
            "cmd": "developer_register",
            "error": "BAD_INPUT",
            "message": "username and password required",
        }

    try:
        accounts_repo.create_developer(username, password, display_name)
    except ValueError as e:
        if str(e) == "USERNAME_TAKEN":
            return {
                "ok": False,
                "cmd": "developer_register",
                "error": "USERNAME_TAKEN",
                "message": "username already taken"
            }
        else:
            return {
                "ok": False,
                "cmd": "developer_register",
                "error": "INTERNAL",
                "message": "internal error"
            }
    print(f"[*] User {username} registered success.")
    return {
        "ok": True,
        "cmd": "developer_register",
        "message": "register success"
    } 

def handle_developer_login(request: dict, session: socket.socket) -> dict:
    username = request.get("username", "").strip()
    password = request.get("password", "")

    if not accounts_repo.verify_developer_password(username, password):
        return {
            "ok": False,
            "cmd": "developer_login",
            "error": "INVALID_CREDENTIALS",
            "message": "invalid username or password"
        }
    
    old_session = online_developers.get(username)
    if old_session is not None and old_session is not session:
        try:
            send_json(old_session, {
                "ok": False,
                "cmd": "force_logout",
                "message": "logged in from another location",
            })
        except Exception:
            pass
        try:
            old_session.close()
        except Exception:
            pass

    # remember connection info
    online_developers[username] = session
    sock_devnames[session] = username

    print(f"[*] User {username} logined success.")
    return {
        "ok": True, 
        "cmd": "player_login",
        "message": "login success"
    }

def handle_developer_create_version(request: dict, sock: socket.socket):
    username = sock_devnames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "NOT_LOGGED_IN",
            "message": "developer login required",
        }
    game_id_raw = request.get("game_id")
    version = request.get("game_version")
    changelog = request.get("changelog") or ""

    try:
        game_id = int(game_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "BAD_INPUT",
            "message": "game_id must be integer",
        }
    if not version:
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "BAD_INPUT",
            "message": "game_version required",
        }
    
    game = games_repo.get_game_by_id(game_id)
    if game is None:
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "NO_SUCH_GAME",
            "message": f"game {game_id} not found",
        }
    
    dev_row = accounts_repo.get_developer_by_username(username)
    if dev_row is None or game["developer_id"] != dev_row["id"]:
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "NOT_OWNER",
            "message": "you are not the developer of this game",
        }
    game_name = game["game_name"]
    
    
    upload_path = f"game_store/{username}/{game_id}_{game_name}/v{version}.zip"
    games_repo.mark_game_active(game_id)
    gamelog_repo.activate_versions_for_game(game_id)

    try:
        version_id = gamelog_repo.create_gamelog(
            game_id=game_id,
            game_version=version,
            changelog=changelog,
            upload_path=upload_path,
            is_active=1,
        )
    except Exception as e:
        return {
            "ok": False,
            "cmd": "developer_create_version",
            "error": "DB_ERROR",
            "message": f"failed to create gamelog: {e}",
        }
    
    return{
        "ok": True,
        "cmd": "developer_create_version",
        "game_id": game_id,
        "version_id": version_id,
        "game_version": version,
        "upload_path": upload_path,
        "message": "version metadata created"
    }

def handle_developer_list_games(request: dict, sock:socket.socket) -> dict:
    username = sock_devnames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "developer_list_games",
            "error": "NOT_LOGGED_IN",
            "message": "developer login required",
        }
    dev = accounts_repo.get_developer_by_username(username)
    if dev is None:
        return {
            "ok": False,
            "cmd": "developer_list_games",
            "error": "NO_SUCH_DEV",
            "message": "developer not found",
        }
    
    dev_id = dev["id"]
    games = games_repo.list_games_by_developer(dev_id)
    result = []
    for g in games:
        latest = gamelog_repo.get_latest_gamelog_for_game(g["id"])
        result.append({
            "game_id": g["id"],
            "game_name": g["game_name"],
            "game_description": g["game_description"],
            "max_players": g["max_players"],
            "latest_version": latest["game_version"] if latest else None,
            "latest_version_id": latest["id"] if latest else None,
        })
    return {
        "ok": True,
        "cmd": "developer_list_games",
        "games": result,
    }

def handle_developer_create_game(request: dict, sock:socket.socket) -> dict:
    username = sock_devnames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "developer_create_game",
            "error": "NOT_LOGGED_IN",
            "message": "developer login required",
        }
    game_name = (request.get("game_name") or "").strip()
    desc = (request.get("game_description") or "").strip()
    max_players_raw = request.get("max_players")

    if not game_name:
        return {
            "ok": False,
            "cmd": "developer_create_game",
            "error": "BAD_INPUT",
            "message": "game_name is required",
        }
    
    try:
        max_players = int(max_players_raw) if max_players_raw is not None else None
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "developer_create_game",
            "error": "BAD_INPUT",
            "message": "max_players must be integer",
        }
    
    dev = accounts_repo.get_developer_by_username(username)

    if dev is None:
        return {
            "ok": False,
            "cmd": "developer_create_game",
            "error": "NO_SUCH_DEV",
            "message": "developer not found",
        }
    
    game_id = games_repo.create_game(dev["id"], game_name, desc, max_players)

    return {
        "ok": True,
        "cmd": "developer_create_game",
        "game_id": game_id,
        "game_name": game_name,
        "message": "game created; please upload first version",
    }

def handle_developer_delete_game(request: dict, sock:socket.socket) -> dict:
    username = sock_devnames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "developer_delete_game",
            "error": "NOT_LOGGED_IN",
            "message": "developer login required",
        }
    game_id_raw = request.get("game_id")
    try:
        game_id = int(game_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "developer_delete_game",
            "error": "BAD_INPUT",
            "message": "game_id must be integer",
        }
    
    game = games_repo.get_game_by_id(game_id)
    if game is None:
        return {
            "ok": False,
            "cmd": "developer_delete_game",
            "error": "NO_SUCH_GAME",
            "message": f"game {game_id} not found",
        }
    dev = accounts_repo.get_developer_by_username(username)
    if dev is None or game["developer_id"] != dev["id"]:
        return {
            "ok": False,
            "cmd": "developer_delete_game",
            "error": "NOT_OWNER",
            "message": "you are not the developer of this game",
        }
    
    games_repo.mark_game_deleted(game_id)
    gamelog_repo.deactivate_versions_for_game(game_id)
    return {
        "ok": True,
        "cmd": "developer_delete_game",
        "game_id": game_id,
        "message": "game marked as deleted",
    }

def handle_get_game_detail(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    devname = sock_devnames.get(sock)
    if not username and not devname:
        return {
            "ok": False,
            "cmd": "get_game_detail", 
            "error": "NOT_LOGGED_IN", 
            "message": "login required"
        }
    
    game_id_raw = request.get("game_id")
    try:
        game_id = int(game_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False, 
            "cmd": "get_game_detail", 
            "error": "BAD_INPUT", 
            "message": "game_id must be integer"
        }
    
    game = games_repo.get_game_by_id(game_id)
    if game is None or game.get("game_status") != "active":
        return {
            "ok": False, 
            "cmd": "get_game_detail", 
            "error": "NO_SUCH_GAME", 
            "message": "game not found"
        }
    latest = gamelog_repo.get_latest_gamelog_for_game(game_id)
    ratings = ratings_repo.list_ratings_for_game(game_id)

    return {
        "ok": True,
        "cmd": "get_game_detail",
        "game": {
            "game_id": game["id"],
            "game_name": game["game_name"],
            "game_description": game.get("game_description") or "",
            "max_players": game.get("max_players"),
            "latest_version": latest.get("game_version") if latest else None,
            "upload_path": latest.get("upload_path") if latest else None,
        },
        "ratings": [
            {
                "player": r.get("player_display_name") or r.get("player_username"),
                "score": r.get("score"),
                "comment": r.get("comment") or "",
                "created_at": r.get("created_at"),
            }
            for r in ratings
        ],
    }

def handle_add_rating(request: dict, sock:socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False, 
            "cmd": "add_rating", 
            "error": "NOT_LOGGED_IN", 
            "message": "player login required"
        }
    game_id_raw = request.get("game_id")
    score_raw = request.get("score")
    comment = (request.get("comment") or "").strip()    
    try:
        game_id = int(game_id_raw)
        score = int(score_raw)
    except (TypeError, ValueError):
        return {
           "ok": False, 
           "cmd": "add_rating", 
           "error": "BAD_INPUT", 
           "message": "game_id/score must be integer" 
        }
    
    if not (1 <= score <= 5):
        return {
            "ok": False, 
            "cmd": "add_rating", 
            "error": "BAD_INPUT", 
            "message": "score must be 1-5"
        }
    
    player = accounts_repo.get_player_by_username(username)
    if player is None:
        return {
            "ok": False, 
            "cmd": "add_rating", 
            "error": "NO_SUCH_PLAYER", 
            "message": "player not found"
        }
    
    check = ratings_repo.has_finished(player["id"], game_id) 
    print("check", check)
    
    if not check:
        return {
            "ok": False, "cmd": "add_rating",
            "error": "NOT_PLAYED",
            "message": "Play the game before rating it",
        }

    
    ratings_repo.add_rating(player["id"], game_id, score, comment)
    ratings = ratings_repo.list_ratings_for_game(game_id)
    return {
        "ok": True,
        "cmd": "add_rating",
        "game_id": game_id,
        "ratings": [
            {
                "player": r.get("player_display_name") or r.get("player_username"),
                "score": r.get("score"),
                "comment": r.get("comment") or "",
                "created_at": r.get("created_at"),
            }
            for r in ratings
        ],
        "message": "rating added",
    }

def handle_start_game(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False, 
            "cmd": "start_game", 
            "error": "NOT_LOGGED_IN", 
            "message": "login required"
        }
    
    room_id_raw = request.get("room_id")
    try:
        room_id = int(room_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False, 
            "cmd": "start_game", 
            "error": "BAD_INPUT", 
            "message": "room_id must be integer"
        }
    
    room = room_states.get(room_id)
    members = room_members.get(room_id) or set()

    if not room or room.get("host") != username:
        return {
            "ok": False, "cmd": "start_game", 
            "error": "NOT_HOST", 
            "message": "only host can start"
        }
    if len(members) < 2:
        return {
            "ok": False, 
            "cmd": "start_game", 
            "error": "NOT_ENOUGH_PLAYERS", 
            "message": "need at least 2 players"
        }
    
    game_host = "127.0.0.1"
    game_port = pick_free_port()
    game_id = room_states[room_id].get("game_id")
    game = games_repo.get_game_by_id(game_id)
    game_log = gamelog_repo.get_latest_gamelog_for_game(game_id)
    game_name = game.get("game_name")
    game_version = game_log.get("game_version")
    developer_id = game.get("developer_id")
    print("dev_id", developer_id)
    dev = accounts_repo.get_developer_by_id(developer_id)
    print("dev", dev)
    dev_name = dev["username"]
    game_server_dir = Path(__file__).parent.parent / "game" / "game_store"/ f"{dev_name}" / f"{game_id}_{game_name}" / f"v{game_version}"
    print("game_server_dir is ",game_server_dir)
    cmd = [sys.executable ,"-m","server.server" , "--host", game_host, "--port", str(game_port), "--room-id", str(room_id)]
    proc = subprocess.Popen(cmd, cwd=game_server_dir)
    game_processes[room_id] = proc

    evt = {
        "cmd": "game_start",
        "room_id": room_id,
        "game_id": room.get("game_id"),
        "game_host": game_host,
        "game_port": game_port,
        "game_version": game_version,
        "game_name": game_name,
        "host_name": username 
    }

    for name in members:
        pinfo = accounts_repo.get_player_by_username(name)
        pid = pinfo["id"]
        psock = online_players.get(name)
        if psock:
            ratings_repo.create_session(pid, game_id)
            
            send_json(psock, evt)

    return {
        "ok": True,
        "cmd": "start_game",
        "room_id": room_id,
        "game_host": game_host,
        "game_port": game_port
    }

def handle_finish_game(request: dict, sock: socket.socket) -> dict:
    username = sock_usernames.get(sock)
    if not username:
        return {
            "ok": False,
            "cmd": "finish_game",
            "error": "NOT_LOGGED_IN",
            "message": "login required",
        }

    room_id_raw = request.get("room_id")
    try:
        room_id = int(room_id_raw)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "cmd": "finish_game",
            "error": "BAD_INPUT",
            "message": "room_id must be integer",
        }
    
    room = room_repo.get_room(room_id)
    if room is None:
        return {
            "ok": False,
            "cmd": "finish_game",
            "error": "NONE_ROOM",
            "message": "room not found",
        }
    game_id = room.get("game_id")

    state = room_states.pop(room_id, None)
    print(state)
    members = room_members.pop(room_id, set())

    # clear user_room mapping
    for name in members:
        pinfo = accounts_repo.get_player_by_username(name)
        pid = pinfo["id"]
        session_id = ratings_repo.search_session(pid, game_id)
        ratings_repo.finish_session(session_id)

    for m in list(members):
        user_room.pop(m, None)


    # # notify others the game/room is closed
    # evt = {
    #     "cmd": "room_closed",
    #     "room_id": room_id,
    #     "message": "game finished, room closed",
    # }
    # for m in members:
    #     psock = online_players.get(m)
    #     if psock:
    #         try:
    #             send_json(psock, evt)
    #         except Exception:
    #             pass

    # stop game process if tracked
    proc = game_processes.pop(room_id, None)
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass

    # delete room in DB
    try:
        room_repo.delete_room(room_id)
    except Exception:
        pass

    return {
        "ok": True,
        "cmd": "finish_game",
        "room_id": room_id,
        "message": "room closed",
    }

def client_thread(sock, addr):
    print(f"[+] New connection from {addr}")
    file = sock.makefile("r", encoding="utf-8")
    try:
        while True:
            req = recv_json(file)
            print(req)
            if req is None:
                break
            
            
            cmd = req.get("cmd", "")
            req_id = req.get("req_id")
            if cmd == "player_register":
                resp = handle_player_register(req)
            elif cmd == "player_login":
                resp = handle_player_login(req, sock)
            elif cmd == "create_room":
                resp = handle_room_create(req, sock)
            elif cmd == "join_room":
                resp = handle_join_room(req, sock)
            elif cmd == "list_rooms":
                resp = handle_list_room(req, sock)
            elif cmd == "leave_room":
                resp = handle_leave_room(req, sock)
            elif cmd == "list_games":
                resp = handle_list_games(req, sock)
            elif cmd == "room_info":
                resp = handle_room_info(req, sock)
            elif cmd == "developer_register":
                resp = handle_developer_register(req)
            elif cmd == "developer_login":
                resp = handle_developer_login(req, sock)
            elif cmd == "developer_create_version":
                resp = handle_developer_create_version(req, sock)
            elif cmd == "developer_list_games":
                resp = handle_developer_list_games(req, sock)
            elif cmd == "developer_create_game":
                resp = handle_developer_create_game(req, sock)
            elif cmd == "developer_delete_game":
                resp = handle_developer_delete_game(req, sock)
            elif cmd == "get_game_detail":
                resp = handle_get_game_detail(req, sock)
            elif cmd == "add_rating":
                resp = handle_add_rating(req, sock)
            elif cmd == "start_game":
                resp = handle_start_game(req, sock)
            elif cmd == "finish_game":
                resp = handle_finish_game(req, sock)

            else:
                resp = {
                    "ok": False,
                    "cmd": cmd,
                    "error": "UNKNOWN_CMD",
                    "message": f"unknown cmd: {cmd}",
                }
            if req_id is not None:
                resp["req_id"] = req_id
            send_json(sock, resp)
    except Exception as e:
        print(f"[!] Error with {addr}: {e}")
    finally:
        username = sock_usernames.pop(sock, None)
        if username is not None:
            if online_players.get(username) is sock:
                del online_players[username]
            
        room_id = user_room.pop(username, None)
        if room_id is None:
            return  

        state = room_states.get(room_id)
        members = room_members.get(room_id, set())
        host = state.get("host")


        if state and host == username:
            evt = {
                "cmd": "room_closed",
                "room_id": room_id,
                "message": f"host {host} left, room closed",
            }

            for name in list(members):
                sock2 = online_players.get(name)
                if sock2 is not None:
                    send_json(sock2, evt)

            for m in list(members):
                user_room.pop(m, None)
            room_states.pop(room_id, None)
            room_members.pop(room_id, None)

        sock.close()
        print(f"[-] Connection closed {addr}")

def handle_shutdown(signum, frame):
    global running
    print("\nShutdown signal received!\n")
    running = False
    # close all connection
    evt = {"cmd": "server_shutdown", "message": "Server shutting down"}
    all_socks = list(sock_usernames.keys()) + list(sock_devnames.keys())
    for sock in all_socks:
        try:
            send_json(sock, evt)
        except Exception:
            pass
        try:
            print(f"sock: {sock} has closed")
            sock.close()
        except Exception:
            pass
    # close all game
    for proc in game_processes.values():
        try:
            proc.terminate()
        except Exception:
            pass
def main():

    signal.signal(signal.SIGINT, handle_shutdown)

    init_db()
    print("[*] DB initialized")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    server.settimeout(0.5)
    
    print(f"[*] Lobby server listening on {HOST}: {PORT}")
    print(f"init running: {running}")
    try:
        while running:
            try:
                client_sock, addr = server.accept()
            except socket.timeout:
                continue
            t = threading.Thread(target=client_thread, args=(client_sock, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nCtrl+C pressed, shutting down...")
    finally:
        server.close()
        print("Server closed.")

if __name__ == "__main__":
    main()
