"""Version Registry REST API — stdlib-only HTTP router.

Returns (status_code, dict) tuples. Designed to be consumed by a web server.
"""

import json
import re
import sqlite3
from typing import Any

from version_registry import VersionRegistry

# Shared global registry instance (lazy-init).
registry = VersionRegistry()


class VersionAPI:
    """Pure-router API. Each method returns ``(status_code, dict_body)``."""

    def __init__(self, reg: VersionRegistry | None = None):
        self.reg = reg or registry

    # ── dispatch ─────────────────────────────────────────────────────

    def dispatch(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, Any]:
        path = path.rstrip("/") if path != "/" else path

        # Literal routes
        literal: dict[tuple[str, str], Any] = {
            ("GET", "/api/versions"): self.list_versions,
            ("GET", "/api/tags"): self.list_tags,
        }
        handler = literal.get((method, path))
        if handler:
            return handler()

        # Pattern-based routes
        # GET /api/versions/{id}
        if method == "GET":
            m = re.match(r"^/api/versions/(v\d+)$", path)
            if m:
                return self.get_version(m.group(1))

        # POST /api/versions
        if method == "POST" and path == "/api/versions":
            return self.create_version(body or {})
        # POST /api/tags
        if method == "POST" and path == "/api/tags":
            return self.create_tag(body or {})
        # POST /api/versions/{id}/live
        if method == "POST":
            m = re.match(r"^/api/versions/(v\d+)/live$", path)
            if m:
                return self.set_live(m.group(1))
            m = re.match(r"^/api/versions/(v\d+)/tags$", path)
            if m:
                return self.tag_version(m.group(1), body or {})

        # PUT /api/versions/{id}
        if method == "PUT":
            m = re.match(r"^/api/versions/(v\d+)$", path)
            if m:
                return self.update_version(m.group(1), body or {})

        return 404, {"error": "Not found"}

    # ── versions ─────────────────────────────────────────────────────

    def list_versions(self) -> tuple[int, Any]:
        versions = self.reg.list_versions()
        for v in versions:
            v["tags"] = self.reg.get_version_tags(str(v["id"]))
        return 200, versions

    def get_version(self, vid: str) -> tuple[int, Any]:
        v = self.reg.get_version(vid)
        if not v:
            return 404, {"error": "Version not found"}
        v["tags"] = self.reg.get_version_tags(vid)
        return 200, v

    def create_version(self, body: dict) -> tuple[int, Any]:
        message = (body.get("message") or "").strip()
        created_by = (body.get("created_by") or "web").strip()
        if not message:
            return 400, {"error": "message is required"}
        try:
            v = self.reg.create_version(created_by=created_by, message=message)
            v["tags"] = []
            return 201, v
        except ValueError as e:
            return 400, {"error": str(e)}

    def set_live(self, vid: str) -> tuple[int, Any]:
        v = self.reg.set_live(vid)
        if not v:
            return 404, {"error": "Version not found"}
        v["tags"] = self.reg.get_version_tags(vid)
        return 200, v

    def update_version(self, vid: str, body: dict) -> tuple[int, Any]:
        allowed = {k: body[k] for k in ("message", "status") if k in body}
        if not allowed:
            return 400, {"error": "No valid fields (message, status)"}
        try:
            v = self.reg.update_version(vid, **allowed)
            if not v:
                return 404, {"error": "Version not found"}
            v["tags"] = self.reg.get_version_tags(vid)
            return 200, v
        except ValueError as e:
            return 400, {"error": str(e)}

    # ── tags ─────────────────────────────────────────────────────────

    def list_tags(self) -> tuple[int, Any]:
        rows = self.reg.conn.execute(
            "SELECT t.*, COUNT(vt.version_id) AS version_count "
            "FROM tags t "
            "LEFT JOIN version_tags vt ON vt.tag_id = t.id "
            "GROUP BY t.id ORDER BY t.name"
        ).fetchall()
        return 200, self._as_dicts(rows)

    def create_tag(self, body: dict) -> tuple[int, Any]:
        name = (body.get("name") or "").strip()
        created_by = (body.get("created_by") or "web").strip()
        if not name:
            return 400, {"error": "name is required"}
        try:
            tag = self.reg.create_tag(name=name, created_by=created_by)
            return 201, tag
        except ValueError as e:
            return 400, {"error": str(e)}

    def tag_version(self, vid: str, body: dict) -> tuple[int, Any]:
        tag_name = (body.get("tag_name") or "").strip()
        if not tag_name:
            return 400, {"error": "tag_name is required"}
        ok = self.reg.tag_version(tag_name, vid)
        if not ok:
            return 404, {
                "error": "Version or tag not found, or already tagged"
            }
        return 200, {"ok": True}

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _as_dicts(rows: Any) -> list[dict]:
        """Convert sqlite3.Row objects to plain dicts if needed."""
        if rows and isinstance(rows[0], sqlite3.Row):
            return [dict(r) for r in rows]
        return rows
