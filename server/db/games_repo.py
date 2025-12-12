from __future__ import annotations
from typing import Optional, List, Dict, Any
from . import get_connection


def get_all_games() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                id,
                developer_id,
                game_name,
                game_description,
                game_version,
                game_status,
                max_players,
                created_at
            FROM games
            WHERE game_status = 'active'
            ORDER BY id
            """
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def get_game_by_id(game_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                id,
                game_name,
                game_description,
                game_status,
                game_version,
                max_players,
                developer_id,
                created_at
            FROM games
            WHERE id = ?
            """,
            (game_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None

def list_games_by_developer(developer_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                id,
                game_name,
                game_description,
                game_version,
                max_players,
                developer_id,
                created_at
            FROM games
            WHERE developer_id = ?
            ORDER BY id
            """,
            (developer_id,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]

def create_game(developer_id: int, game_name: str, game_description: str, max_players: int | None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO games (developer_id, game_name, game_description, max_players, game_status)
            VALUES(?, ?, ?, ?, 'active')
            """,
            (developer_id, game_name, game_description, max_players),
        )
        return cur.lastrowid
    
def mark_game_deleted(game_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE games SET game_status='deleted' WHERE id = ?
            """,
            (game_id,),
        )

def mark_game_active(game_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE games SET game_status='active' WHERE id = ?
            """,
            (game_id,),
        )

