import asyncio
import json
import os
import time

import aiohttp

from .discovery import default_discovery

PROXY_DEFAULT_FIELDS = [
    {"name": "agent_id", "type": "string"},
    {"name": "status", "type": "string"},
    {"name": "pid", "type": "int"},
    {"name": "cpu", "type": "float", "label": "CPU%"},
    {"name": "mem_pct", "type": "float", "label": "MEM%"},
    {"name": "window", "type": "string"},
    {"name": "last_active", "type": "float"},
]

KNOWN_PROVIDERS = {
    "openai": {"upstream": "https://api.openai.com", "api_key_env": "OPENAI_API_KEY"},
    "anthropic": {"upstream": "https://api.anthropic.com", "api_key_env": "ANTHROPIC_API_KEY"},
    "opencode": {"upstream": "https://opencode.ai/go/v1", "api_key_env": "OPENCODE_API_KEY"},
}


def infer_provider(name):
    name_lower = name.lower()
    if name_lower in KNOWN_PROVIDERS:
        return name_lower
    for key in KNOWN_PROVIDERS:
        if key in name_lower:
            return key
    return None


class ProxyInlineHandler:
    """Handles proxy discovery and agent tracking within the main app."""

    def __init__(self, app, pcfg, name):
        self.app = app
        self.pcfg = pcfg
        self.name = name
        self._agents = {}
        self._running = True

    async def start_discovery(self):
        discovery_fn = self.pcfg.get("discovery", default_discovery)
        while self._running:
            try:
                discovered = discovery_fn()
                current_ids = {a["agent_id"] for a in discovered}
                for agent in discovered:
                    aid = agent["agent_id"]
                    if aid in self._agents:
                        self._agents[aid].update(agent)
                    else:
                        self._agents[aid] = agent
                for aid in list(self._agents.keys()):
                    if aid not in current_ids:
                        if self._agents[aid]["status"] != "idle":
                            self._agents[aid]["status"] = "idle"
                now = time.time()
                for agent in self._agents.values():
                    if agent["status"] == "active" and now - agent["last_active"] > 120:
                        agent["status"] = "idle"
                # Push to DB so CRUD can serve it
                tbl = self.name.split('/')[-1]
                if self.name in self.app._model_schema:
                    db = self.app._pool.get(self.app._model_db.get(self.name, "default"))
                    if db:
                        try:
                            existing = db.list(tbl)
                            existing_ids = {e.get("agent_id") for e in existing if e.get("agent_id")}
                            current_ids = {a["agent_id"] for a in self._agents.values()}
                            # Delete agents that are no longer present
                            for e in existing:
                                if e.get("agent_id") and e["agent_id"] not in current_ids:
                                    db.delete(tbl, e["id"])
                            # Upsert agents
                            for agent in self._agents.values():
                                existing_match = [e for e in existing if e.get("agent_id") == agent["agent_id"]]
                                if existing_match:
                                    db.update(tbl, existing_match[0]["id"], agent)
                                else:
                                    db.create(tbl, agent)
                        except Exception:
                            pass
            except Exception:
                pass
            await asyncio.sleep(10)

    def get_agents(self):
        return list(self._agents.values())

    def close(self):
        self._running = False


class ProxyBackend:
    """Standalone proxy server on a separate port."""

    def __init__(self, app, pcfg, name):
        self.app = app
        self.pcfg = pcfg
        self.name = name
        self._server = None
        self._inline = ProxyInlineHandler(app, pcfg, name)
        self._session = None

    async def start(self, host, port):
        self._resolved_key = self._resolve_api_key()
        self._upstream = self.pcfg.get("upstream")
        self._session = aiohttp.ClientSession()
        self._server = await asyncio.start_server(
            self._handle_connection, host, port
        )
        asyncio.create_task(self._inline.start_discovery())
        return port

    def _resolve_api_key(self):
        pcfg = self.pcfg
        if pcfg.get("api_key"):
            return pcfg["api_key"]
        if pcfg.get("api_key_env"):
            return os.environ.get(pcfg["api_key_env"])
        env_var = f"{pcfg['cls'].__name__.upper()}_API_KEY"
        return os.environ.get(env_var)

    async def _handle_connection(self, reader, writer):
        try:
            raw = b""
            while True:
                chunk = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=30)
                raw += chunk
                if b"\r\n\r\n" in raw:
                    break

            header_part, _, body = raw.partition(b"\r\n\r\n")
            lines = header_part.decode("utf-8", errors="replace").split("\r\n")
            if not lines or not lines[0]:
                writer.close()
                return

            request_line = lines[0]
            parts = request_line.split(" ")
            method = parts[0]
            path = parts[1]

            headers = {}
            content_length = 0
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                    if k.lower() == "content-length":
                        content_length = int(v.strip())

            if method in ("POST", "PUT") and content_length > 0:
                while len(body) < content_length:
                    chunk = await asyncio.wait_for(reader.read(65536), timeout=30)
                    if not chunk:
                        break
                    body += chunk

            if method == "GET" and (path == f"/{self.name}" or path == f"/{self.name}/"):
                resp_body = json.dumps(self._inline.get_agents())
                writer.write((
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(resp_body)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "\r\n"
                ).encode() + resp_body.encode())
                await writer.drain()
                writer.close()
                return

            if self._upstream:
                upstream_url = f"{self._upstream}{path}"
                try:
                    async with self._session.request(
                        method, upstream_url,
                        headers={k: v for k, v in headers.items() if k.lower() not in ("host", "content-length", "transfer-encoding")},
                        data=body if method in ("POST", "PUT") else None,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        resp_headers = dict(resp.headers)
                        resp_body = await resp.read()
                        status = resp.status

                        for log_name in self.app._log_models:
                            log_db = self.app._pool.get(self.app._model_db.get(log_name, "default"))
                            if log_db:
                                ts = __import__("time").strftime("%H:%M:%S")
                                log_db.create(log_name.split('/')[-1], {
                                    "source": self.name,
                                    "level": "info",
                                    "content": f"{method} {path} → {status}",
                                    "time": ts,
                                })
                                log_db.engine._conn.execute(
                                    f"DELETE FROM {log_name.split('/')[-1]} WHERE id NOT IN (SELECT id FROM {log_name.split('/')[-1]} ORDER BY id DESC LIMIT 200)"
                                )
                                log_db.engine._conn.commit()

                        resp_line = f"HTTP/1.1 {status} {resp.reason or ''}\r\n"
                        for k, v in resp_headers.items():
                            if k.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                                resp_line += f"{k}: {v}\r\n"
                        resp_line += f"Content-Length: {len(resp_body)}\r\n\r\n"
                        writer.write(resp_line.encode() + resp_body)
                        await writer.drain()
                except Exception as e:
                    error = json.dumps({"error": str(e)})
                    writer.write((
                        "HTTP/1.1 502 Bad Gateway\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(error)}\r\n"
                        "\r\n"
                    ).encode() + error.encode())
                    await writer.drain()
            else:
                writer.write((
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Length: 0\r\n"
                    "\r\n"
                ).encode())
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def close(self):
        self._inline.close()
        if self._session:
            await self._session.close()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
