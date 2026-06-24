"""Portable leaderboard storage: Supabase Postgres in production, SQLite locally."""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path


class LeaderboardUnavailable(RuntimeError):
    pass


class NicknameTaken(ValueError):
    pass


class LeaderboardStore:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.mode = "supabase-postgres" if self.database_url else "local-sqlite"

    def status(self) -> dict:
        return {"mode": self.mode, "configured": bool(self.database_url)}

    def _sqlite_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE IF NOT EXISTS users (token TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        connection.execute("CREATE TABLE IF NOT EXISTS picks (token TEXT NOT NULL, fixture_key TEXT NOT NULL, prediction TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (token, fixture_key))")
        return connection

    def _postgres_connection(self):
        try:
            import psycopg
            from psycopg.rows import dict_row

            connection = psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=8)
            connection.execute("CREATE TABLE IF NOT EXISTS users (token TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TIMESTAMPTZ DEFAULT NOW())")
            connection.execute("CREATE TABLE IF NOT EXISTS picks (token TEXT NOT NULL REFERENCES users(token) ON DELETE CASCADE, fixture_key TEXT NOT NULL, prediction TEXT NOT NULL CHECK (prediction IN ('home', 'draw', 'away')), updated_at TIMESTAMPTZ DEFAULT NOW(), PRIMARY KEY (token, fixture_key))")
            # The browser never reads these tables through Supabase's Data API.
            # RLS therefore provides a safe default if the project exposes public tables.
            connection.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
            connection.execute("ALTER TABLE picks ENABLE ROW LEVEL SECURITY")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_lower_name_unique ON users (lower(name))")
            connection.commit()
            return connection
        except Exception as error:
            raise LeaderboardUnavailable("The configured Supabase database is unavailable.") from error

    def _connection(self):
        return self._postgres_connection() if self.database_url else self._sqlite_connection()

    def register(self, name: str, token: str | None = None) -> dict:
        connection = self._connection()
        try:
            placeholder = "%s" if self.database_url else "?"
            if token:
                user = connection.execute(f"SELECT token FROM users WHERE token = {placeholder}", (token,)).fetchone()
                if user:
                    duplicate = connection.execute(f"SELECT token FROM users WHERE lower(name) = lower({placeholder}) AND token != {placeholder}", (name, token)).fetchone()
                    if duplicate:
                        raise NicknameTaken("That nickname is already in use.")
                    connection.execute(f"UPDATE users SET name = {placeholder} WHERE token = {placeholder}", (name, token))
                    connection.commit()
                    return {"token": token, "name": name, "existing": True}

            existing = connection.execute(f"SELECT token FROM users WHERE lower(name) = lower({placeholder})", (name,)).fetchone()
            if existing:
                raise NicknameTaken("That nickname is already in use. Choose another one.")
            new_token = uuid.uuid4().hex
            connection.execute(f"INSERT INTO users (token, name) VALUES ({placeholder}, {placeholder})", (new_token, name))
            connection.commit()
            return {"token": new_token, "name": name, "existing": False}
        finally:
            connection.close()

    def save_pick(self, token: str, fixture_key: str, prediction: str) -> str | None:
        connection = self._connection()
        try:
            placeholder = "%s" if self.database_url else "?"
            user = connection.execute(f"SELECT name FROM users WHERE token = {placeholder}", (token,)).fetchone()
            if not user:
                return None
            if self.database_url:
                connection.execute(
                    "INSERT INTO picks (token, fixture_key, prediction) VALUES (%s, %s, %s) "
                    "ON CONFLICT(token, fixture_key) DO UPDATE SET prediction = EXCLUDED.prediction, updated_at = NOW()",
                    (token, fixture_key, prediction),
                )
            else:
                connection.execute(
                    "INSERT INTO picks (token, fixture_key, prediction) VALUES (?, ?, ?) "
                    "ON CONFLICT(token, fixture_key) DO UPDATE SET prediction = excluded.prediction, updated_at = CURRENT_TIMESTAMP",
                    (token, fixture_key, prediction),
                )
            connection.commit()
            return user["name"]
        finally:
            connection.close()

    def entries(self) -> list[dict]:
        connection = self._connection()
        try:
            return [dict(row) for row in connection.execute("SELECT users.name, picks.fixture_key, picks.prediction FROM users LEFT JOIN picks ON users.token = picks.token").fetchall()]
        finally:
            connection.close()
