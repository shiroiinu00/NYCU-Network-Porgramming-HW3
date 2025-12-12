from __future__ import annotations
from typing import List, Dict, Any
from . import get_connection

def add_rating(player_id: int, game_id: int, score: int, comment: str):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO ratings (player_id, game_id, score, comment)
            VALUES (?, ?, ?, ?)
            """
            ,(player_id, game_id, score, comment),
        )
        return cur.lastrowid
    
def list_ratings_for_game (game_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                r.id,
                r.score,
                r.comment,
                r.created_at,
                p.username AS player_username,
                p.display_name as player_display_name
            FROM ratings r
            JOIN players p ON r.player_id = p.id
            WHERE r.game_id = ?
            ORDER BY r.created_at DESC, r.id DESC
            """,
            (game_id,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def create_session(player_id, game_id, game_version_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO player_sessions(player_id, game_id, game_version_id)
               VALUES (?, ?, ?)""",
            (player_id, game_id, game_version_id),
        )
        return cur.lastrowid
    
def search_session(player_id, game_id):
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT id from player_sessions WHERE player_id=? and game_id=?""",
            (player_id, game_id),
        )
        return cur.lastrowid

def finish_session(session_id, result=None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE player_sessions SET finished_at=CURRENT_TIMESTAMP, result=? WHERE id=?",
            (result, session_id),
        )

def has_finished(player_id, game_id) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT 1 FROM player_sessions
               WHERE player_id=? AND game_id=? AND started_at IS NOT NULL
               LIMIT 1""",
            (player_id, game_id),
        )
        return cur.fetchone() is not None