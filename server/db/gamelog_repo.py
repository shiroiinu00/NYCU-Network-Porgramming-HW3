from __future__ import annotations
from typing import Optional, Dict, Any, List
from . import get_connection

def create_gamelog(game_id: int, game_version: str, changelog: str, upload_path: str, is_active: int = 1) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO gamelog (game_id, game_version, changelog, upload_path, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, game_version, changelog, upload_path, is_active),
        )
        return cur.lastrowid

def get_latest_gamelog_for_game(game_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                id,
                game_id,
                game_version,
                changelog,
                upload_path,
                is_active,
                uploaded_at
            FROM gamelog
            WHERE game_id = ?
            AND is_active = 1
            ORDER BY uploaded_at DESC, id DESC
            LIMIT 1
            """,
            (game_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None

def list_games_with_latest_version() -> List[Dict[str, Any]]:
    from .games_repo import get_all_games

    games = get_all_games()
    result: List[Dict[str, Any]] = []

    with get_connection() as conn:
        for g in games:
            game_id = g["id"]
            cur = conn.execute(
                """
                SELECT
                    id,
                    game_version,
                    upload_path,
                    uploaded_at
                FROM gamelog
                WHERE game_id = ?
                AND is_active = 1
                ORDER BY uploaded_at DESC, id DESC
                LIMIT 1
                """,
                (game_id,),
            )
            row = cur.fetchone()
            latest_version = None
            latest_version_id = None
            upload_path = None
            if row:
                latest_version_id = row["id"]
                latest_version = row["game_version"]
                upload_path = row["upload_path"]
            
            result.append(
                {
                    "game_id": game_id,
                    "game_name": g["game_name"],
                    "game_description": g["game_description"],
                    "max_players": g["max_players"],
                    "latest_version": latest_version,
                    "latest_version_id": latest_version_id,
                    "upload_path": upload_path,
                }

            )

    return result

def deactivate_versions_for_game(game_id: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE gamelog SET is_active = 0 WHERE game_id = ?",
            (game_id,),
        )

def activate_versions_for_game(game_id: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE gamelog SET is_active = 1 WHERE game_id = ?",
            (game_id,),
        )

        