from __future__ import annotations
import hashlib
import sqlite3

from . import get_connection

def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

# player
def create_player(username: str, raw_password: str, display_name: str):
    password_hash = _hash_password(raw_password)
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (username, password_hash, display_name) VALUES (?, ?, ?)         
                """,
                (username, password_hash, display_name),
            )
    except sqlite3.IntegrityError as e:
        raise ValueError("USERNAME_TAKEN") from e
    
def get_player_by_username(username: str):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM players WHERE username = ?",
            (username,),
        )
        return cur.fetchone()
    
def verify_player_password(username: str, raw_password: str):
    row = get_player_by_username(username)
    if row is None:
        return False
    
    expected_hash = row["password_hash"]
    return expected_hash == _hash_password(raw_password)

# developer
def create_developer(username: str, raw_password: str, display_name: str):
    password_hash = _hash_password(raw_password)
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO developers (username, password_hash, display_name) VALUES (?, ?, ?)         
                """,
                (username, password_hash, display_name),
            )
    except sqlite3.IntegrityError as e:
        raise ValueError("USERNAME_TAKEN") from e


def get_developer_by_username(username: str):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM developers WHERE username = ?",
            (username,),
        )
        return cur.fetchone()
def get_developer_by_id(id: str):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM developers WHERE id = ?",
            (id,),
        )
        return cur.fetchone()
    
def verify_developer_password(username: str, raw_password: str):
    row = get_developer_by_username(username)
    if row is None:
        return False
    
    expected_hash = row["password_hash"]
    return expected_hash == _hash_password(raw_password)
    # return True
    
