"""NOVA Auto-Layer — self-discovering, self-assembling application runtime.

The auto-layer introspects models and specs, then generates
routes, UI screens, and pipelines at runtime without manual coding.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Optional

from ..core import Config, VISIBILITY
from ..meta import Spec, ModelSpec, RouteSpec


class AutoDiscover:
    """Discovers models, routes, and capabilities at runtime."""

    def __init__(self, config: Config, spec: Optional[Spec] = None):
        self.config = config
        self.spec = spec
        self._models: dict[str, dict] = {}
        self._routes: list[dict] = []
        self._capabilities: dict[str, bool] = {}

    def discover_models(self) -> dict[str, dict]:
        """Introspect available data models (from spec + runtime)."""
        models = {}
        if self.spec:
            for m in self.spec.models:
                models[m.name] = {
                    "name": m.name,
                    "fields": {f.name: {"type": f.type, "required": f.required,
                                         "unique": f.unique, "default": f.default}
                              for f in m.fields},
                    "relationships": [{"model": r.model, "cardinality": r.cardinality}
                                      for r in m.relationships],
                }
        self._models = models
        return models

    def discover_routes(self) -> list[dict]:
        """Discover available routes (from spec + auto-generated)."""
        routes = []
        if self.spec:
            for r in self.spec.routes:
                routes.append({
                    "pattern": r.pattern,
                    "methods": r.methods,
                    "model": r.model,
                    "permissions": r.permissions,
                    "ai_powered": r.ai_powered,
                    "generator": r.generator,
                })
        # Auto-generate CRUD routes for models without explicit routes
        if self.spec:
            routed_models = {r.model for r in self.spec.routes if r.model}
            for m in self.spec.models:
                if m.name not in routed_models:
                    base = f"/api/{m.name.lower()}s"
                    routes.extend([
                        {"pattern": base, "methods": ["GET", "POST"],
                         "model": m.name, "auto": True},
                        {"pattern": f"{base}/{{id}}", "methods": ["GET", "PUT", "DELETE"],
                         "model": m.name, "auto": True},
                    ])
        self._routes = routes
        return routes

    def discover_capabilities(self) -> dict[str, bool]:
        """Discover what capabilities are available at runtime."""
        caps = {}
        # Check AI providers
        caps["ai.generate"] = bool(self.config.ai.primary.key or
                                    os.getenv("OPENCODE_GO_API_KEY"))
        caps["ai.embed"] = bool(os.getenv("OPENAI_API_KEY"))
        # Check sources
        for name, src in self.config.sources.items():
            caps[f"source.{name}"] = src.enabled
        # Check file system
        caps["storage.local"] = True
        caps["media.compose"] = bool(Path(self.config.assets_dir).exists())
        self._capabilities = caps
        return caps

    def get_summary(self) -> dict:
        """Full runtime introspection summary."""
        return {
            "models": self.discover_models(),
            "routes": self.discover_routes(),
            "capabilities": self.discover_capabilities(),
            "sources": {k: v.enabled for k, v in self.config.sources.items()},
        }


class AutoRouter:
    """Generates FastAPI routes dynamically from discovered models."""

    def __init__(self, discover: AutoDiscover):
        self.discover = discover

    def mount_on(self, app: "FastAPI"):
        """Mount auto-discovered routes on a FastAPI app."""
        from fastapi import APIRouter

        router = APIRouter(tags=["auto"])

        routes = self.discover.discover_routes()
        models = self.discover.discover_models()

        if not routes:
            VISIBILITY.log("WARN", "autorouter", "No routes to mount (spec is None?)",
                           {"has_spec": self.discover.spec is not None})
            return

        for route in routes:
            if route.get("auto", False):
                # Auto-generated CRUD → /auto prefix
                auto_router = APIRouter(prefix="/auto", tags=["auto-crud"])
                self._add_crud_route(auto_router, route, models)
                app.include_router(auto_router)
            elif route.get("generator"):
                self._add_generator_route(router, route)
            else:
                self._add_crud_route(router, route, models)

        app.include_router(router)
        VISIBILITY.action("autorouter.mount",
                          f"Mounted {len(routes)} auto-routes")

    def _add_crud_route(self, router: "APIRouter", route: dict, models: dict):
        """Add a CRUD route dynamically."""
        import fastapi

        methods = route["methods"]
        pattern = route["pattern"]
        model_name = route.get("model", "")

        if "GET" in methods:
            @router.get(pattern)
            async def auto_list():
                return {
                    "auto": True,
                    "model": model_name,
                    "route": pattern,
                    "items": [],
                }

            if "{id}" in pattern:
                @router.get(pattern)
                async def auto_get(id: str):
                    return {"auto": True, "model": model_name, "id": id}

        if "POST" in methods:
            @router.post(pattern)
            async def auto_create(data: dict = None):
                return {"auto": True, "model": model_name, "status": "created"}

    def _add_generator_route(self, router: "APIRouter", route: dict):
        """Add a generator/feed route."""

        @router.get(route["pattern"])
        async def auto_generator():
            return {
                "auto": True,
                "route": route["pattern"],
                "generator": True,
                "status": "ready",
            }


class AutoUIRenderer:
    """Renders UI components from schema (no manual templates needed)."""

    def render_model_form(self, model_name: str, fields: dict) -> str:
        """Generate a form HTML from model fields."""
        inputs = ""
        for fname, finfo in fields.items():
            ftype = finfo.get("type", "string")
            required = "required" if finfo.get("required") else ""
            placeholder = fname.replace("_", " ").title()

            if ftype == "text":
                inputs += f'  <textarea name="{fname}" {required} placeholder="{placeholder}" class="auto-field"></textarea>\n'
            elif ftype == "bool":
                checked = 'checked' if finfo.get("default") else ''
                inputs += f'  <label class="auto-checkbox"><input type="checkbox" name="{fname}" {checked}> {placeholder}</label>\n'
            elif ftype == "int" or ftype == "float":
                inputs += f'  <input type="number" name="{fname}" {required} placeholder="{placeholder}" class="auto-field" />\n'
            elif ftype == "email":
                inputs += f'  <input type="email" name="{fname}" {required} placeholder="{placeholder}" class="auto-field" />\n'
            else:
                inputs += f'  <input type="text" name="{fname}" {required} placeholder="{placeholder}" class="auto-field" />\n'

        return f'''<div class="auto-form" id="form-{model_name.lower()}">
  <h3>New {model_name}</h3>
  <form onsubmit="return autoSubmit('{model_name.lower()}', event)">
{inputs}
    <button type="submit">Create {model_name}</button>
  </form>
</div>'''

    def render_feed(self, model_name: str) -> str:
        """Generate an infinite feed component."""
        return f'''<div class="auto-feed" id="feed-{model_name.lower()}">
  <div class="feed-items" id="{model_name.lower()}-feed-items">
    <!-- Auto-loaded items appear here -->
  </div>
  <div class="feed-loader" id="{model_name.lower()}-loader">Loading...</div>
</div>'''

    def render_dashboard(self, models: dict) -> str:
        """Generate a dashboard from all models."""
        cards = ""
        for name, info in models.items():
            field_count = len(info.get("fields", {}))
            cards += f'''<div class="dash-card" onclick="location.href='/auto/ui/{name}'">
  <div class="dash-card-title">{name}</div>
  <div class="dash-card-stat">{field_count}</div>
  <div class="dash-card-label">fields</div>
</div>'''
        return f'<div class="auto-dashboard">{cards}</div>'

    def render_page(self, title: str, content: str) -> str:
        """Wrap content in a full page with auto-styles."""
        return f'''<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font:14px/1.5 system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:900px;margin:auto}}
.auto-form{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin:16px 0}}
.auto-field{{width:100%;padding:8px 12px;margin:4px 0 12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:14px}}
.auto-field:focus{{border-color:#58a6ff;outline:none}}
.auto-checkbox{{display:flex;align-items:center;gap:8px;margin:8px 0;cursor:pointer}}
button{{background:#238636;border:none;color:#fff;padding:8px 20px;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600}}
button:hover{{background:#2ea043}}
.auto-feed{{margin:16px 0}}
.feed-items{{min-height:200px}}
.feed-loader{{text-align:center;color:#8b949e;padding:20px}}
.auto-dashboard{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin:16px 0}}
.dash-card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;cursor:pointer;text-align:center}}
.dash-card:hover{{border-color:#58a6ff}}
.dash-card-title{{font-size:13px;color:#8b949e;text-transform:uppercase;margin-bottom:8px}}
.dash-card-stat{{font-size:36px;font-weight:700;color:#58a6ff}}
.dash-card-label{{font-size:11px;color:#8b949e;margin-top:4px}}
h3{{margin-bottom:12px;color:#58a6ff}}
</style>
<script>
async function autoSubmit(model, e){{
  e.preventDefault();const f=new FormData(e.target);const d=Object.fromEntries(f);
  const r=await fetch('/auto/api/'+model+'s',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(d)}});
  const j=await r.json();alert('Created: '+JSON.stringify(j));return false;
}}
</script>
</head>
<body>
{content}
</body>
</html>'''
