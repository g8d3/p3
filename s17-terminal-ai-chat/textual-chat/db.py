"""Database module for Terminal AI Chat App."""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

DATABASE_PATH = "chat_app.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            provider_type TEXT NOT NULL,
            api_key TEXT,
            base_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER,
            name TEXT NOT NULL,
            model_id TEXT NOT NULL,
            context_length INTEGER DEFAULT 4096,
            cost_per_1k_tokens REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            system_prompt TEXT,
            model_id INTEGER,
            tools TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            agent_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            latency_ms REAL DEFAULT 0.0,
            cost REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            code TEXT NOT NULL,
            parameters TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            cron_expression TEXT,
            agent_id INTEGER,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            next_run TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    """)

    conn.commit()
    conn.close()


class ProviderDB:
    @staticmethod
    def create(name: str, provider_type: str, api_key: str = None, base_url: str = None) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO providers (name, provider_type, api_key, base_url) VALUES (?, ?, ?, ?)",
            (name, provider_type, api_key, base_url)
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['name', 'provider_type', 'api_key', 'base_url']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if not kwargs:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE providers SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM providers WHERE id = ?", (id,))
        conn.commit()
        conn.close()


class ModelDB:
    @staticmethod
    def create(provider_id: int, name: str, model_id: str, context_length: int = 4096, cost_per_1k_tokens: float = 0.0) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO models (provider_id, name, model_id, context_length, cost_per_1k_tokens) VALUES (?, ?, ?, ?, ?)",
            (provider_id, name, model_id, context_length, cost_per_1k_tokens)
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM models ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM models WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['provider_id', 'name', 'model_id', 'context_length', 'cost_per_1k_tokens']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if not kwargs:
            return
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE models SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM models WHERE id = ?", (id,))
        conn.commit()
        conn.close()


class AgentDB:
    @staticmethod
    def create(name: str, system_prompt: str = None, model_id: int = None, tools: List[str] = None) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agents (name, system_prompt, model_id, tools) VALUES (?, ?, ?, ?)",
            (name, system_prompt, model_id, json.dumps(tools or []))
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['name', 'system_prompt', 'model_id', 'tools']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if 'tools' in kwargs:
            kwargs['tools'] = json.dumps(kwargs['tools'])
        if not kwargs:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE agents SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agents WHERE id = ?", (id,))
        conn.commit()
        conn.close()


class SessionDB:
    @staticmethod
    def create(name: str = None, agent_id: int = None) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (name, agent_id) VALUES (?, ?)",
            (name, agent_id)
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['name', 'agent_id']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if not kwargs:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (id,))
        conn.commit()
        conn.close()


class MessageDB:
    @staticmethod
    def create(session_id: int, role: str, content: str, tokens_in: int = 0, tokens_out: int = 0, latency_ms: float = 0.0, cost: float = 0.0) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, tokens_in, tokens_out, latency_ms, cost) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, role, content, tokens_in, tokens_out, latency_ms, cost)
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_by_session(session_id: int) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def delete_by_session(session_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()


class ToolDB:
    @staticmethod
    def create(name: str, code: str, description: str = None, parameters: Dict = None) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tools (name, description, code, parameters) VALUES (?, ?, ?, ?)",
            (name, description, code, json.dumps(parameters or {}))
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tools ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tools WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['name', 'description', 'code', 'parameters']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if 'parameters' in kwargs:
            kwargs['parameters'] = json.dumps(kwargs['parameters'])
        if not kwargs:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE tools SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tools WHERE id = ?", (id,))
        conn.commit()
        conn.close()


class ScheduleDB:
    @staticmethod
    def create(name: str, cron_expression: str, agent_id: int = None, enabled: bool = True) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schedules (name, cron_expression, agent_id, enabled) VALUES (?, ?, ?, ?)",
            (name, cron_expression, agent_id, 1 if enabled else 0)
        )
        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def get_all() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(id: int, **kwargs):
        allowed = ['name', 'cron_expression', 'agent_id', 'enabled', 'last_run', 'next_run']
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        if 'enabled' in kwargs and isinstance(kwargs['enabled'], bool):
            kwargs['enabled'] = 1 if kwargs['enabled'] else 0
        if not kwargs:
            return
        kwargs['updated_at'] = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs])
        cursor.execute(f"UPDATE schedules SET {set_clause} WHERE id = ?", (*kwargs.values(), id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schedules WHERE id = ?", (id,))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized at", DATABASE_PATH)
