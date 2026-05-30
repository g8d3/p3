"""NOVA Server — chat-first SPA with setup wizard, streaming chat, and live preview."""

from __future__ import annotations
import json
import os
import sys
import time
import asyncio
from typing import Optional
from pathlib import Path

from ..core import Config, VISIBILITY
from .spa import build_spa, create_defaults


def _resolve_key(key: str) -> str:
    """Resolve an API key — if it starts with $, read from env var."""
    if key and key.startswith("$"):
        return os.environ.get(key[1:], "")
    return key


def check_provider_blocking(url: str, model: str, key: str) -> dict:
    """Synchronous provider check — runs in executor."""
    import urllib.request
    import json
    key = _resolve_key(key)
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "respond with just: ok"}],
        "max_tokens": 10,
    }).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        r = urllib.request.urlopen(req, timeout=15)
        resp = json.loads(r.read())
        content = resp["choices"][0]["message"]["content"]
        return {"ok": True, "model": model, "response": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class NovaServer:
    """NOVA web server — serves the SPA and handles chat/API."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._provider = {
            "url": "",
            "model": "",
            "key": "",
            "configured": False,
        }
        self._app_generated = False
        self._app_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load_provider(self):
        """Load provider from config/env."""
        d = create_defaults()
        self._provider["url"] = os.getenv("LLM_URL", d["provider_url"])
        self._provider["model"] = os.getenv("LLM_MODEL", d["provider_model"])
        self._provider["key"] = os.getenv("LLM_API_KEY", "")
        self._provider["configured"] = bool(self._provider.get("key") or
                                             "localhost" in self._provider.get("url", ""))

    def build_app(self):
        """Build the FastAPI application."""
        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI(title="NOVA")
        app.add_middleware(CORSMiddleware, allow_origins=["*"],
                           allow_methods=["*"], allow_headers=["*"])

        self._load_provider()

        # ── SPA — single page app ──
        @app.get("/")
        async def root():
            html = build_spa(
                configured=self._provider["configured"],
                provider=self._provider["url"],
                model=self._provider["model"],
            )
            return HTMLResponse(html)

        # ── Provider test ──
        @app.post("/api/provider/test")
        async def provider_test(data: dict):
            url = data.get("url", "")
            model = data.get("model", "")
            key = _resolve_key(data.get("key", ""))
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: check_provider_blocking(url, model, key))
            return result

        # ── Provider configure ──
        @app.post("/api/provider/configure")
        async def provider_configure(data: dict):
            self._provider["url"] = data.get("url", self._provider["url"])
            self._provider["model"] = data.get("model", self._provider["model"])
            raw_key = data.get("key", "")
            self._provider["key"] = _resolve_key(raw_key)
            self._provider["_raw_key"] = raw_key
            self._provider["configured"] = True
            # Save to env for subprocesses
            os.environ["LLM_URL"] = self._provider["url"]
            os.environ["LLM_MODEL"] = self._provider["model"]
            os.environ["LLM_API_KEY"] = self._provider["key"]
            VISIBILITY.action("provider.configured",
                              f"Provider: {self._provider['model']}")
            return {"status": "ok", "model": self._provider["model"]}

        # ── Provider disconnect ──
        @app.post("/api/provider/disconnect")
        async def provider_disconnect():
            self._provider = {"url": "", "model": "", "key": "", "configured": False}
            for k in ["LLM_URL", "LLM_MODEL", "LLM_API_KEY"]:
                os.environ.pop(k, None)
            VISIBILITY.action("provider.disconnected", "Provider disconnected")
            return {"status": "ok"}

        # ── Streaming Chat ──
        @app.post("/api/chat")
        async def chat(data: dict):
            message = data.get("message", "")
            if not message:
                return JSONResponse({"error": "empty message"}, status_code=400)

            return StreamingResponse(
                chat_stream(message, self._provider),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # ── Health ──
        @app.get("/api/health")
        async def health():
            return {
                "status": "ok",
                "app": "NOVA",
                "configured": self._provider["configured"],
                "model": self._provider["model"] if self._provider["configured"] else None,
            }

        # ── Status ──
        @app.get("/api/status")
        async def status():
            return {
                "provider_configured": self._provider["configured"],
                "provider_model": self._provider["model"],
                "app_generated": self._app_generated,
                "uptime_s": time.time() - _start_time if '_start_time' in dir() else 0,
            }

        return app


async def chat_stream(message: str, provider: dict):
    """Stream chat responses via SSE with tool calling."""

    # System prompt
    system = (
        "Eres NOVA, un asistente que crea aplicaciones web completas. "
        "Tus herramientas disponibles:\n"
        "1. generate_app(description) — crea una app desde una descripción\n"
        "2. modify_app(cambios) — modifica la app actual\n"
        "3. run_tests() — ejecuta los tests\n"
        "4. get_status() — estado del sistema\n\n"
        "Sé conversacional pero directo. Cuando generes código, explicá brevemente lo que hiciste.\n"
        "Respondé SIEMPRE en español."
    )

    # Call the LLM
    url = provider.get("url", "")
    model = provider.get("model", "")
    key = _resolve_key(provider.get("key", ""))

    # Try streaming first, fallback to non-streaming
    payload_stream = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": True,
    }).encode()

    payload_nonstream = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": False,
    }).encode()

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        import urllib.request
        loop = asyncio.get_running_loop()

        # Try streaming first
        req = urllib.request.Request(url, data=payload_stream, headers=headers)
        try:
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=120))

            full_text = ""
            buffer = ""

            while True:
                chunk = await loop.run_in_executor(
                    None, lambda: resp.read(4096))
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='replace')

                # Parse SSE lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            parsed = json.loads(data)
                            delta = parsed.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_text += content
                                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
                        except json.JSONDecodeError:
                            pass
        except Exception as stream_err:
            # Fallback to non-streaming
            VISIBILITY.log("DEBUG", "chat", f"Stream failed, falling back: {stream_err}")
            req2 = urllib.request.Request(url, data=payload_nonstream, headers=headers)
            resp2 = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req2, timeout=120))
            result = json.loads(await loop.run_in_executor(
                None, lambda: resp2.read().decode()))
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not content:
                content = result.get('choices', [{}])[0].get('message', {}).get('reasoning_content', '')
            # Strip thinking/ reasoning if present (some models return it in content)
            if content and 'Thinking.' in content[:20]:
                content = ''
            if content:
                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"

        # After response, try to detect if they want an app generated
        msg_lower = message.lower()
        create_keywords = ['crea', 'genera', 'haz', 'construye', 'crear', 'generar',
                           'una app', 'un crm', 'un blog', 'un clon', 'un sistema',
                           'un feed', 'un chat', 'un ecommerce', 'un dashboard']
        if any(kw in msg_lower for kw in create_keywords):
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'generate_app', 'params': message[:100]})}\n\n"
            # Generate app files from spec
            app_path = await generate_app_from_description(message)
            if app_path:
                yield f"data: {json.dumps({'type': 'tool_result', 'result': f'App generada en {app_path}'})}\n\n"
                yield f"data: {json.dumps({'type': 'app_updated', 'url': '/'})}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


async def generate_app_from_description(description: str) -> Optional[str]:
    """Generate an app from a natural language description."""
    from ..meta import Spec, ModelSpec, FieldSpec, RouteSpec, CodeGenerator

    # Simple intent parsing — extract model names from description
    desc_lower = description.lower()
    models = []

    # Common patterns
    if any(w in desc_lower for w in ['crm', 'cliente', 'clients', 'lead']):
        models.append(ModelSpec(
            name="Client",
            fields=[
                FieldSpec(name="name", type="string", required=True),
                FieldSpec(name="email", type="email"),
                FieldSpec(name="phone", type="string"),
                FieldSpec(name="company", type="string"),
                FieldSpec(name="notes", type="text"),
                FieldSpec(name="status", type="string", default="active"),
            ],
        ))

    if any(w in desc_lower for w in ['tiktok', 'video', 'feed', 'short']):
        models.append(ModelSpec(
            name="Video",
            fields=[
                FieldSpec(name="title", type="string", required=True),
                FieldSpec(name="url", type="string", required=True),
                FieldSpec(name="description", type="text"),
                FieldSpec(name="duration_s", type="float"),
                FieldSpec(name="author", type="string"),
                FieldSpec(name="likes", type="int", default=0),
                FieldSpec(name="created_at", type="datetime"),
            ],
        ))

    if any(w in desc_lower for w in ['blog', 'post', 'artículo', 'articulo']):
        models.append(ModelSpec(
            name="Post",
            fields=[
                FieldSpec(name="title", type="string", required=True),
                FieldSpec(name="slug", type="string", unique=True),
                FieldSpec(name="body", type="text", required=True),
                FieldSpec(name="excerpt", type="text"),
                FieldSpec(name="published", type="bool", default=False),
                FieldSpec(name="views", type="int", default=0),
            ],
        ))

    if any(w in desc_lower for w in ['user', 'usuario', 'perfil', 'profile', 'auth']):
        models.append(ModelSpec(
            name="User",
            fields=[
                FieldSpec(name="name", type="string", required=True),
                FieldSpec(name="email", type="email", unique=True),
                FieldSpec(name="avatar", type="string"),
                FieldSpec(name="role", type="string", default="user"),
            ],
        ))

    # Generic fallback — create a basic app
    if not models:
        models.append(ModelSpec(
            name="Item",
            fields=[
                FieldSpec(name="title", type="string", required=True),
                FieldSpec(name="description", type="text"),
                FieldSpec(name="status", type="string", default="active"),
            ],
        ))

    # Build routes
    routes = []
    for m in models:
        base = f"/api/{m.name.lower()}s"
        routes.append(RouteSpec(pattern=base, methods=["GET", "POST"], model=m.name))
        routes.append(RouteSpec(pattern=f"{base}/{{id}}", methods=["GET", "PUT", "DELETE"],
                                 model=m.name))

    routes.append(RouteSpec(pattern="/api/feed", methods=["GET"], generator=True))

    # Create spec
    import re
    # Sanitize app name
    desc_clean = description.lower().strip()
    # Remove leading articles and common prefixes
    for prefix in ['una ', 'un ', 'crea una ', 'crea un ', 'crear una ', 'crear un ',
                   'haz una ', 'haz un ', 'genera una ', 'genera un ']:
        if desc_clean.startswith(prefix):
            desc_clean = desc_clean[len(prefix):]
            break
    name_match = re.match(r'(\w+)', desc_clean)
    app_name = "mi-app"
    if name_match:
        name = name_match.group(1).replace("_", "-")
        if name not in ("app", "app", "aplicacion", "sistema", "que"):
            app_name = name

    spec = Spec(
        name=app_name,
        description=description[:200],
        models=models,
        routes=routes,
    )

    # Generate code
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "generated", app_name.replace("-", "_"))
    gen = CodeGenerator()
    written = gen.write_all(spec, base_dir)

    VISIBILITY.action("app.generated",
                      f"App '{app_name}' with {len(models)} models, {len(written)} files")
    return base_dir


_start_time = time.time()
