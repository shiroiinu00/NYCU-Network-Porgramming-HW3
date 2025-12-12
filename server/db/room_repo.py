from __future__ import annotations

import sqlite3

from typing import Optional
from . import get_connection
from.games_repo import get_game_by_id

def create_room(host_player_id: int, game_id: int, max_players: int) -> int:
    with get_connection() as conn:
        game = get_game_by_id(game_id)
        game_name = game["game_name"]
        cur = conn.execute(
            """
            INSERT INTO rooms (host_player_id, game_id, max_players, game_name)
            VALUES (?, ?, ?, ?)
            """,
            (host_player_id, game_id, max_players, game_name,),
        )
        room_id = cur.lastrowid
    return room_id

def get_room(room_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT host_player_id, game_id, max_players, game_name 
            FROM rooms
            WHERE id = ?
            """,
            (room_id,)
        )
        row = cur.fetchone()
    return dict(row) if row else None

def delete_room(room_id: int) -> None:
    with get_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM rooms
            WHERE id = ?
            """,
            (room_id,)
        )
        cur2 = conn.execute(
            """
            SELECT * FROM rooms
            """,
        )
        # rows = cur2.fetchall(); print(len(rows))