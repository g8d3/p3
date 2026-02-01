"""SQLite database models and CRUD operations."""

import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class Provider:
    """Provider model."""
    
    id: str
    name: str
    provider_type: str
    api_key: Optional[str]
    base_url: Optional[str]
    enabled: bool
    extra: str
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Provider":
        return cls(**data)


@dataclass
class Model:
    """Model configuration model."""
    
    id: str
    name: str
    provider_name: str
    model_id: str
    context_window: int
    max_tokens: int
    cost_per_input: float
    cost_per_output: float
    is_default: bool
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Model":
        return cls(**data)


@dataclass
class Agent:
    """Agent model."""
    
    id: str
    name: str
    system_prompt: str
    provider_name: str
    model_name: str
    tools: str
    enabled: bool
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Agent":
        return cls(**data)


@dataclass
class Session:
    """Chat session model."""
    
    id: str
    name: str
    agent_id: Optional[str]
    provider_name: str
    model_name: str
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        return cls(**data)


@dataclass
class Message:
    """Chat message model."""
    
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: Optional[str]
    tool_results: Optional[str]
    tokens_in: int
    tokens_out: int
    latency_ms: float
    ttft_ms: float
    cost: float
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(**data)


@dataclass
class Tool:
    """Tool model."""
    
    id: str
    name: str
    description: str
    parameters: str
    function: str
    enabled: bool
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Tool":
        return cls(**data)


@dataclass
class Schedule:
    """Scheduled task model."""
    
    id: str
    name: str
    agent_id: str
    prompt: str
    schedule_type: str
    schedule_value: str
    enabled: bool
    last_run: Optional[str]
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Schedule":
        return cls(**data)


@dataclass
class APILog:
    """API request/response log."""
    
    id: str
    session_id: str
    provider_name: str
    model_name: str
    request_type: str
    request_data: str
    response_data: Optional[str]
    status_code: Optional[int]
    error: Optional[str]
    tokens_in: int
    tokens_out: int
    latency_ms: float
    ttft_ms: float
    cost: float
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "APILog":
        return cls(**data)


class Database:
    """SQLite database manager."""
    
    def __init__(self, db_path: str):
        self.db_path = os.path.expanduser(db_path)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS providers (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    provider_type TEXT NOT NULL,
                    api_key TEXT,
                    base_url TEXT,
                    enabled INTEGER DEFAULT 1,
                    extra TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    context_window INTEGER DEFAULT 128000,
                    max_tokens INTEGER DEFAULT 4096,
                    cost_per_input REAL DEFAULT 0.0,
                    cost_per_output REAL DEFAULT 0.0,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider_name, model_id)
                );
                
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    system_prompt TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    tools TEXT DEFAULT '[]',
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    agent_id TEXT,
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_results TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    latency_ms REAL DEFAULT 0.0,
                    ttft_ms REAL DEFAULT 0.0,
                    cost REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                CREATE TABLE IF NOT EXISTS tools (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    function TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                );
                
                CREATE TABLE IF NOT EXISTS api_logs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    request_data TEXT NOT NULL,
                    response_data TEXT,
                    status_code INTEGER,
                    error TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    latency_ms REAL DEFAULT 0.0,
                    ttft_ms REAL DEFAULT 0.0,
                    cost REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_api_logs_session ON api_logs(session_id);
                CREATE INDEX IF NOT EXISTS idx_api_logs_created ON api_logs(created_at);
            """)
            conn.commit()
    
    def create_provider(self, provider: Provider) -> Provider:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO providers (id, name, provider_type, api_key, base_url, enabled, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (provider.id, provider.name, provider.provider_type, 
                  provider.api_key, provider.base_url, 
                  int(provider.enabled), provider.extra))
            conn.commit()
        return provider
    
    def get_providers(self, enabled_only: bool = False) -> List[Provider]:
        with self.get_connection() as conn:
            query = "SELECT * FROM providers"
            if enabled_only:
                query += " WHERE enabled = 1"
            rows = conn.execute(query).fetchall()
            return [Provider(**dict(row)) for row in rows]
    
    def get_provider(self, name: str) -> Optional[Provider]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM providers WHERE name = ?", (name,)).fetchone()
            return Provider(**dict(row)) if row else None
    
    def update_provider(self, provider: Provider) -> Provider:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE providers SET name=?, provider_type=?, api_key=?, base_url=?, 
                enabled=?, extra=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (provider.name, provider.provider_type, provider.api_key,
                  provider.base_url, int(provider.enabled), provider.extra, provider.id))
            conn.commit()
        return provider
    
    def delete_provider(self, name: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM providers WHERE name = ?", (name,))
            conn.commit()
    
    def create_model(self, model: Model) -> Model:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO models (id, name, provider_name, model_id, context_window, max_tokens,
                cost_per_input, cost_per_output, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model.id, model.name, model.provider_name, model.model_id,
                  model.context_window, model.max_tokens, model.cost_per_input,
                  model.cost_per_output, int(model.is_default)))
            conn.commit()
        return model
    
    def get_models(self, provider_name: Optional[str] = None) -> List[Model]:
        with self.get_connection() as conn:
            if provider_name:
                rows = conn.execute("SELECT * FROM models WHERE provider_name = ?", (provider_name,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM models").fetchall()
            return [Model(**dict(row)) for row in rows]
    
    def get_model(self, provider_name: str, model_id: str) -> Optional[Model]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM models WHERE provider_name = ? AND model_id = ?",
                (provider_name, model_id)
            ).fetchone()
            return Model(**dict(row)) if row else None
    
    def update_model(self, model: Model) -> Model:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE models SET name=?, provider_name=?, model_id=?, context_window=?,
                max_tokens=?, cost_per_input=?, cost_per_output=?, is_default=?,
                updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (model.name, model.provider_name, model.model_id,
                  model.context_window, model.max_tokens, model.cost_per_input,
                  model.cost_per_output, int(model.is_default), model.id))
            conn.commit()
        return model
    
    def delete_model(self, id: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM models WHERE id = ?", (id,))
            conn.commit()
    
    def create_agent(self, agent: Agent) -> Agent:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agents (id, name, system_prompt, provider_name, model_name, tools, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (agent.id, agent.name, agent.system_prompt, agent.provider_name,
                  agent.model_name, agent.tools, int(agent.enabled)))
            conn.commit()
        return agent
    
    def get_agents(self, enabled_only: bool = False) -> List[Agent]:
        with self.get_connection() as conn:
            query = "SELECT * FROM agents"
            if enabled_only:
                query += " WHERE enabled = 1"
            rows = conn.execute(query).fetchall()
            return [Agent(**dict(row)) for row in rows]
    
    def get_agent(self, name: str) -> Optional[Agent]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
            return Agent(**dict(row)) if row else None
    
    def get_agent_by_id(self, id: str) -> Optional[Agent]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM agents WHERE id = ?", (id,)).fetchone()
            return Agent(**dict(row)) if row else None
    
    def update_agent(self, agent: Agent) -> Agent:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE agents SET name=?, system_prompt=?, provider_name=?, model_name=?,
                tools=?, enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (agent.name, agent.system_prompt, agent.provider_name,
                  agent.model_name, agent.tools, int(agent.enabled), agent.id))
            conn.commit()
        return agent
    
    def delete_agent(self, name: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM agents WHERE name = ?", (name,))
            conn.commit()
    
    def create_session(self, session: Session) -> Session:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (id, name, agent_id, provider_name, model_name)
                VALUES (?, ?, ?, ?, ?)
            """, (session.id, session.name, session.agent_id,
                  session.provider_name, session.model_name))
            conn.commit()
        return session
    
    def get_sessions(self) -> List[Session]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
            return [Session(**dict(row)) for row in rows]
    
    def get_session(self, id: str) -> Optional[Session]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (id,)).fetchone()
            return Session(**dict(row)) if row else None
    
    def update_session(self, session: Session) -> Session:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE sessions SET name=?, agent_id=?, provider_name=?, model_name=?,
                updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (session.name, session.agent_id, session.provider_name,
                  session.model_name, session.id))
            conn.commit()
        return session
    
    def delete_session(self, id: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (id,))
            conn.execute("DELETE FROM api_logs WHERE session_id = ?", (id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (id,))
            conn.commit()
    
    def create_message(self, message: Message) -> Message:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO messages (id, session_id, role, content, tool_calls, tool_results,
                tokens_in, tokens_out, latency_ms, ttft_ms, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message.id, message.session_id, message.role, message.content,
                  message.tool_calls, message.tool_results, message.tokens_in,
                  message.tokens_out, message.latency_ms, message.ttft_ms, message.cost))
            conn.commit()
        return message
    
    def get_messages(self, session_id: str) -> List[Message]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            ).fetchall()
            return [Message(**dict(row)) for row in rows]
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as message_count,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(cost) as total_cost,
                    AVG(latency_ms) as avg_latency,
                    SUM(tokens_out) * 1000.0 / SUM(latency_ms) as tokens_per_second
                FROM messages 
                WHERE session_id = ?
            """, (session_id,)).fetchone()
            return dict(stats) if stats else {}
    
    def create_tool(self, tool: Tool) -> Tool:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO tools (id, name, description, parameters, function, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tool.id, tool.name, tool.description, tool.parameters,
                  tool.function, int(tool.enabled)))
            conn.commit()
        return tool
    
    def get_tools(self, enabled_only: bool = False) -> List[Tool]:
        with self.get_connection() as conn:
            query = "SELECT * FROM tools"
            if enabled_only:
                query += " WHERE enabled = 1"
            rows = conn.execute(query).fetchall()
            return [Tool(**dict(row)) for row in rows]
    
    def get_tool(self, name: str) -> Optional[Tool]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM tools WHERE name = ?", (name,)).fetchone()
            return Tool(**dict(row)) if row else None
    
    def update_tool(self, tool: Tool) -> Tool:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE tools SET name=?, description=?, parameters=?, function=?,
                enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (tool.name, tool.description, tool.parameters,
                  tool.function, int(tool.enabled), tool.id))
            conn.commit()
        return tool
    
    def delete_tool(self, name: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM tools WHERE name = ?", (name,))
            conn.commit()
    
    def create_schedule(self, schedule: Schedule) -> Schedule:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO schedules (id, name, agent_id, prompt, schedule_type, schedule_value, enabled, last_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (schedule.id, schedule.name, schedule.agent_id, schedule.prompt,
                  schedule.schedule_type, schedule.schedule_value, int(schedule.enabled), schedule.last_run))
            conn.commit()
        return schedule
    
    def get_schedules(self, enabled_only: bool = False) -> List[Schedule]:
        with self.get_connection() as conn:
            query = "SELECT * FROM schedules"
            if enabled_only:
                query += " WHERE enabled = 1"
            rows = conn.execute(query).fetchall()
            return [Schedule(**dict(row)) for row in rows]
    
    def get_schedule(self, name: str) -> Optional[Schedule]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM schedules WHERE name = ?", (name,)).fetchone()
            return Schedule(**dict(row)) if row else None
    
    def update_schedule(self, schedule: Schedule) -> Schedule:
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE schedules SET name=?, agent_id=?, prompt=?, schedule_type=?,
                schedule_value=?, enabled=?, last_run=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (schedule.name, schedule.agent_id, schedule.prompt,
                  schedule.schedule_type, schedule.schedule_value, int(schedule.enabled),
                  schedule.last_run, schedule.id))
            conn.commit()
        return schedule
    
    def delete_schedule(self, name: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM schedules WHERE name = ?", (name,))
            conn.commit()
    
    def create_api_log(self, log: APILog) -> APILog:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO api_logs (id, session_id, provider_name, model_name, request_type,
                request_data, response_data, status_code, error, tokens_in, tokens_out,
                latency_ms, ttft_ms, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log.id, log.session_id, log.provider_name, log.model_name,
                  log.request_type, log.request_data, log.response_data,
                  log.status_code, log.error, log.tokens_in, log.tokens_out,
                  log.latency_ms, log.ttft_ms, log.cost))
            conn.commit()
        return log
    
    def get_api_logs(self, session_id: str, limit: int = 100) -> List[APILog]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM api_logs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
            return [APILog(**dict(row)) for row in rows]
    
    def get_recent_api_logs(self, limit: int = 50) -> List[APILog]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM api_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [APILog(**dict(row)) for row in rows]
    
    def get_provider_stats(self, provider_name: str, days: int = 7) -> Dict[str, Any]:
        with self.get_connection() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as request_count,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(cost) as total_cost,
                    AVG(latency_ms) as avg_latency,
                    AVG(ttft_ms) as avg_ttft,
                    SUM(tokens_out) * 1000.0 / SUM(latency_ms) as tokens_per_second
                FROM api_logs 
                WHERE provider_name = ? AND created_at >= datetime('now', ?)
            """, (provider_name, f'-{days} days')).fetchone()
            return dict(stats) if stats else {}
    
    def get_all_time_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(cost) as total_cost,
                    AVG(latency_ms) as avg_latency,
                    AVG(ttft_ms) as avg_ttft
                FROM api_logs
            """).fetchone()
            return dict(stats) if stats else {}
