"""Code Generator — generates models, routes, UI, and tests from Spec."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any

from .spec import Spec, ModelSpec, RouteSpec
from ..core.logging import VISIBILITY


class ModelGenerator:
    """Generates Python data models from Spec."""

    TYPE_MAP = {
        "string": "str",
        "text": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "email": "str",
        "url": "str",
        "json": "dict",
        "datetime": "str",
        "date": "str",
    }

    def generate(self, model: ModelSpec) -> str:
        lines = [f"class {model.name}:"]
        if model.fields:
            lines.append("    \"\"\"Auto-generated model.\"\"\"")
            lines.append("")
            for f in model.fields:
                py_type = self.TYPE_MAP.get(f.type, "Any")
                default = ""
                if f.required:
                    default = "  # required"
                elif f.default is not None:
                    default = f" = {repr(f.default)}"
                else:
                    default = " = None"
                lines.append(f"    {f.name}: {py_type}{default}")
        else:
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def generate_sqlalchemy(self, model: ModelSpec) -> str:
        table = model.table_name or model.name.lower()
        lines = [f"class {model.name}(Base):",
                 f'    __tablename__ = "{table}"',
                 f'    __table_args__ = {{"extend_existing": True}}',
                 ""]
        lines.append("    id = Column(Integer, primary_key=True)")
        for f in model.fields:
            col_type = {
                "string": "String(255)",
                "text": "Text",
                "int": "Integer",
                "float": "Float",
                "bool": "Boolean",
                "json": "JSON",
                "datetime": "DateTime",
                "email": "String(255)",
                "url": "String(512)",
            }.get(f.type, "String(255)")
            nullable = "nullable=True" if not f.required else ""
            unique = "unique=True" if f.unique else ""
            default = f"default={repr(f.default)}" if f.default is not None else ""
            opts = ", ".join(filter(None, [nullable, unique, default]))
            lines.append(f"    {f.name} = Column({col_type}{', ' + opts if opts else ''})")
        lines.append("")
        return "\n".join(lines)


class RouteGenerator:
    """Generates API route files from Spec."""

    def generate(self, routes: list[RouteSpec], models: list[ModelSpec]) -> str:
        lines = ['"""Auto-generated API routes."""',
                 "from fastapi import APIRouter, HTTPException",
                 "from pydantic import BaseModel",
                 "",
                 "router = APIRouter()",
                 ""]
        for route in routes:
            model_name = route.model
            methods = route.methods or ["GET"]

            if "GET" in methods and route.pattern.endswith("/{id}"):
                lines.append("")
                lines.append(f"@router.get(\"{route.pattern}\")")
                lines.append(f"async def get_{model_name.lower()}(id: str):")
                lines.append(f'    """Get {model_name} by ID."""')
                lines.append("    return {\"id\": id, \"model\": \"" + model_name + "\"}")
                lines.append("")

            if "GET" in methods and route.pattern.endswith("s"):
                lines.append("")
                lines.append(f"@router.get(\"{route.pattern}\")")
                lines.append(f"async def list_{model_name.lower()}s():")
                lines.append(f'    """List all {model_name.lower()}s."""')
                lines.append("    return {\"items\": [], \"total\": 0}")
                lines.append("")

            if "POST" in methods:
                lines.append("")
                lines.append(f"class {model_name}Create(BaseModel):")
                lines.append("    pass")
                lines.append("")
                lines.append(f"@router.post(\"{route.pattern}\")")
                lines.append(f"async def create_{model_name.lower()}(data: {model_name}Create):")
                lines.append(f'    """Create {model_name}."""')
                lines.append("    return {\"status\": \"created\", \"data\": data}")
                lines.append("")

        return "\n".join(lines)


class UIGenerator:
    """Generates UI component skeletons."""

    def generate_feed(self) -> str:
        return '<div id="feed" class="infinite-feed">\n  <!-- Auto-generated feed -->\n</div>'

    def generate_form(self, model: ModelSpec) -> str:
        fields_html = ""
        for f in model.fields:
            if f.type == "text":
                fields_html += f'  <textarea name="{f.name}" placeholder="{f.name}"></textarea>\n'
            else:
                fields_html += f'  <input type="text" name="{f.name}" placeholder="{f.name}" />\n'
        return f'<form id="{model.name.lower()}-form">\n{fields_html}</form>'

    def generate_player(self) -> str:
        return '<div id="player" class="fullscreen-player">\n  <video id="bg-video" autoplay loop></video>\n  <div id="subs"></div>\n  <div id="controls" class="overlay"></div>\n</div>'


class TestGenerator:
    """Generates test files from Spec."""

    def generate_model_tests(self, model: ModelSpec) -> str:
        return f'''"""Tests for {model.name} model."""
import pytest


def test_{model.name.lower()}_create():
    """Test creating a {model.name}."""
    assert True


def test_{model.name.lower()}_validation():
    """Test {model.name} field validation."""
    assert True


def test_{model.name.lower()}_relations():
    """Test {model.name} relationships."""
    assert True
'''

    def generate_api_tests(self, route: RouteSpec) -> str:
        path = route.pattern.replace("{id}", "test-123")
        return f'''"""Tests for {route.pattern}."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_{route.model.lower()}_list(client: AsyncClient):
    r = await client.get("{route.pattern}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_{route.model.lower()}_create(client: AsyncClient):
    r = await client.post("{route.pattern}", json={{}})
    assert r.status_code in (200, 201)
'''


class CodeGenerator:
    """Orchestrates code generation from a complete Spec."""

    def __init__(self, output_dir: str = "generated"):
        self.output_dir = Path(output_dir)
        self.model_gen = ModelGenerator()
        self.route_gen = RouteGenerator()
        self.ui_gen = UIGenerator()
        self.test_gen = TestGenerator()

    def generate_all(self, spec: Spec) -> dict[str, str]:
        """Generate all code from spec. Returns {path: content} map."""
        files = {}

        # Models
        for model in spec.models:
            content = self.model_gen.generate_sqlalchemy(model)
            path = f"models/{model.name.lower()}.py"
            files[path] = content

        # Routes
        if spec.routes:
            content = self.route_gen.generate(spec.routes, spec.models)
            files["routes/api.py"] = content

        # UI screens
        if spec.ui.layout == "feed":
            files["ui/feed.html"] = self.ui_gen.generate_feed()
        if spec.ui.layout == "player":
            files["ui/player.html"] = self.ui_gen.generate_player()
        for model in spec.models:
            files[f"ui/forms/{model.name.lower()}.html"] = self.ui_gen.generate_form(model)

        # Tests
        for model in spec.models:
            files[f"tests/test_{model.name.lower()}.py"] = \
                self.test_gen.generate_model_tests(model)
        for route in spec.routes:
            if route.model:
                files[f"tests/test_{route.model.lower()}_api.py"] = \
                    self.test_gen.generate_api_tests(route)

        # __init__.py files
        files["models/__init__.py"] = "\n".join(
            f"from .{m.name.lower()} import {m.name}"
            for m in spec.models
        )
        files["routes/__init__.py"] = "from .api import router\n"

        # Main entry point
        files["main.py"] = self._generate_main(spec)

        VISIBILITY.action("codegen", f"Generated {len(files)} files from spec '{spec.name}'",
                          {"files": list(files.keys())})
        return files

    def _generate_main(self, spec: Spec) -> str:
        return f'''"""Auto-generated entry point for {spec.name} v{spec.version}."""
from fastapi import FastAPI
from routes import router

app = FastAPI(title="{spec.name}", version="{spec.version}")
app.include_router(router)


@app.get("/")
async def root():
    return {{"app": "{spec.name}", "version": "{spec.version}"}}
'''

    def write_all(self, spec: Spec, base_dir: str = ".") -> list[str]:
        """Generate and write all files to disk."""
        files = self.generate_all(spec)
        written = []
        for rel_path, content in files.items():
            full_path = os.path.join(base_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            written.append(full_path)
        return written

    def generate_prompt(self, spec: Spec) -> str:
        """Generate a prompt that describes the spec for AI agents."""
        parts = [f"# {spec.name} v{spec.version}",
                 f"{spec.description}",
                 "",
                 "## Models"]
        for m in spec.models:
            fields = ", ".join(f"{f.name}: {f.type}" for f in m.fields)
            parts.append(f"- **{m.name}**: {fields}")
        parts.append("")
        parts.append("## Routes")
        for r in spec.routes:
            parts.append(f"- {' '.join(r.methods)} {r.pattern}")
        parts.append("")
        parts.append("## AI Capabilities: " + ", ".join(spec.ai.capabilities))
        return "\n".join(parts)
