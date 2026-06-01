"""Version Registry — manage versions, tags, and agent work metadata.

Provides a VersionRegistry class backed by SQLite (aan.db) with the exact
schema defined in SCHEMA.md. Supports creating/promoting versions, tagging,
tag relations, and recording agent work per version.
"""

import os
import sqlite3
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Optional


_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aan.db")
_LIVE_SYMLINK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live")
_VERSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "versions")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _next_version_id(cursor: sqlite3.Cursor) -> str:
    """Return the next auto-incrementing version id (v001, v002, …)."""
    cursor.execute("SELECT id FROM versions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row is None:
        return "v001"
    last = row["id"]
    match = re.search(r"v(\d+)$", last)
    if not match:
        return "v001"
    return f"v{int(match.group(1)) + 1:03d}"


def _ensure_versions_dir(path: str) -> None:
    """Create the versions directory (and parents) if it does not exist."""
    os.makedirs(path, exist_ok=True)


_ROWS_CLS = dict | sqlite3.Row


# ---------------------------------------------------------------------------
# VersionRegistry
# ---------------------------------------------------------------------------

class VersionRegistry:
    """SQLite-backed registry for app version snapshots, tags, and agent work.

    Parameters
    ----------
    db_path : str, optional
        Path to the SQLite database file. Defaults to ``aan.db`` next to this
        module.
    row_factory : type, optional
        Row factory for query results — ``dict`` (default) or ``sqlite3.Row``.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        *,
        row_factory: type = dict,
    ) -> None:
        self._db_path = db_path or _DB_PATH
        self._row_factory = row_factory
        self._conn: Optional[sqlite3.Connection] = None

    # ---- connection -------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazily-initialised SQLite connection with the schema applied."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            if self._row_factory is dict:
                self._conn.row_factory = lambda cur, row: dict(
                    zip([col[0] for col in cur.description], row)
                )
            else:
                self._conn.row_factory = self._row_factory
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS versions (
                id          TEXT PRIMARY KEY,
                parent_id   TEXT REFERENCES versions(id),
                created_by  TEXT NOT NULL,
                message     TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'draft',
                path        TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                live        INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                created_by  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS version_tags (
                version_id  TEXT NOT NULL REFERENCES versions(id),
                tag_id      INTEGER NOT NULL REFERENCES tags(id),
                PRIMARY KEY (version_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS tag_relations (
                tag1_id     INTEGER NOT NULL REFERENCES tags(id),
                tag2_id     INTEGER NOT NULL REFERENCES tags(id),
                relation    TEXT NOT NULL,
                PRIMARY KEY (tag1_id, tag2_id, relation)
            );

            CREATE TABLE IF NOT EXISTS agent_work (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id  TEXT NOT NULL REFERENCES versions(id),
                agent_type  TEXT NOT NULL,
                input_spec  TEXT,
                output_log  TEXT,
                exit_status TEXT NOT NULL DEFAULT 'ok',
                started_at  TEXT,
                finished_at TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_version_live
                ON versions(live) WHERE live = 1;
        """)
        self._conn.commit()

    # ---- helpers ----------------------------------------------------------

    def _row(self, sql: str, params: Sequence[Any] = ()) -> Optional[dict | sqlite3.Row]:
        cursor = self.conn.execute(sql, params)
        return cursor.fetchone()

    def _all_rows(self, sql: str, params: Sequence[Any] = ()) -> list[dict | sqlite3.Row]:
        cursor = self.conn.execute(sql, params)
        return cursor.fetchall()

    # ---- versions ---------------------------------------------------------

    def create_version(
        self,
        created_by: str,
        message: str,
        *,
        parent_id: Optional[str] = None,
        status: str = "draft",
    ) -> dict | sqlite3.Row:
        """Create a new version and return its record.

        The ``id`` is auto-incremented (v001, v002, …). A corresponding
        directory ``versions/<id>/`` is created on the filesystem.

        Parameters
        ----------
        created_by : str
            Who or what created this version ("human", "builder", …).
        message : str
            Description of what changed / why.
        parent_id : str, optional
            The version this was forked from.
        status : str, optional
            Initial status (default ``"draft"``).

        Returns
        -------
        dict or sqlite3.Row
            The newly inserted version row.
        """
        if not created_by.strip():
            raise ValueError("created_by must not be empty")
        if not message.strip():
            raise ValueError("message must not be empty")

        _ensure_versions_dir(_VERSIONS_DIR)
        cursor = self.conn.cursor()
        vid = _next_version_id(cursor)
        ver_path = os.path.join(_VERSIONS_DIR, vid)
        os.makedirs(ver_path, exist_ok=True)

        cursor.execute(
            """INSERT INTO versions (id, parent_id, created_by, message, status, path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vid, parent_id, created_by, message, status, ver_path),
        )
        self.conn.commit()
        return self.get_version(vid)  # type: ignore[return-value]

    def get_version(self, version_id: str) -> Optional[dict | sqlite3.Row]:
        """Retrieve a version by its id.

        Parameters
        ----------
        version_id : str
            The version id (e.g. ``"v001"``).

        Returns
        -------
        dict or sqlite3.Row or None
            The version record, or ``None`` if not found.
        """
        return self._row("SELECT * FROM versions WHERE id = ?", (version_id,))

    def list_versions(
        self,
        *,
        status: Optional[str] = None,
        order: str = "DESC",
    ) -> list[dict | sqlite3.Row]:
        """List all versions, newest first by default.

        Parameters
        ----------
        status : str, optional
            If provided, filter by this status.
        order : str, optional
            Sort order — ``"ASC"`` or ``"DESC"`` (default).

        Returns
        -------
        list[dict or sqlite3.Row]
            The matching version records.
        """
        if status:
            rows = self._all_rows(
                "SELECT * FROM versions WHERE status = ? ORDER BY id " + order,
                (status,),
            )
        else:
            rows = self._all_rows(
                "SELECT * FROM versions ORDER BY id " + order,
            )
        return rows

    def update_version(
        self,
        version_id: str,
        **fields: Any,
    ) -> Optional[dict | sqlite3.Row]:
        """Update one or more columns of a version record.

        Acceptable keys: ``parent_id``, ``created_by``, ``message``,
        ``status``, ``path``.

        Parameters
        ----------
        version_id : str
            The version to update.
        **fields
            Column names and their new values.

        Returns
        -------
        dict or sqlite3.Row or None
            The updated version, or ``None`` if not found.
        """
        allowed = {"parent_id", "created_by", "message", "status", "path"}
        provided = set(fields)
        bad = provided - allowed
        if bad:
            raise ValueError(f"Unknown field(s): {', '.join(sorted(bad))}")
        if not provided:
            raise ValueError("At least one field to update is required")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        params = list(fields.values()) + [version_id]
        self.conn.execute(
            f"UPDATE versions SET {set_clause} WHERE id = ?",
            params,
        )
        self.conn.commit()
        return self.get_version(version_id)

    def set_live(self, version_id: str) -> Optional[dict | sqlite3.Row]:
        """Set a version as the single live (production) version.

        Any previously live version is automatically demoted. A symlink
        ``live → versions/<version_id>/`` is created/updated on the
        filesystem.

        Parameters
        ----------
        version_id : str
            The version to promote.

        Returns
        -------
        dict or sqlite3.Row or None
            The promoted version record, or ``None`` if not found.
        """
        ver = self.get_version(version_id)
        if ver is None:
            return None

        self.conn.execute("UPDATE versions SET live = 0 WHERE live = 1")
        self.conn.execute(
            "UPDATE versions SET live = 1 WHERE id = ?", (version_id,),
        )
        self.conn.commit()

        # Manage symlink.
        target = os.path.join(_VERSIONS_DIR, version_id)
        _update_symlink(_LIVE_SYMLINK, target)

        return self.get_version(version_id)

    def get_live(self) -> Optional[dict | sqlite3.Row]:
        """Return the currently live version, or ``None`` if no live version exists."""
        return self._row("SELECT * FROM versions WHERE live = 1")

    # ---- tags -------------------------------------------------------------

    def create_tag(self, name: str, created_by: str) -> dict | sqlite3.Row:
        """Create a new tag.

        Parameters
        ----------
        name : str
            Unique tag name (e.g. ``"ui"``, ``"bugfix"``).
        created_by : str
            Who or what created this tag.

        Returns
        -------
        dict or sqlite3.Row
            The newly inserted tag record.
        """
        if not name.strip():
            raise ValueError("tag name must not be empty")
        if not created_by.strip():
            raise ValueError("created_by must not be empty")

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tags (name, created_by) VALUES (?, ?)",
            (name, created_by),
        )
        self.conn.commit()
        return self._row("SELECT * FROM tags WHERE id = ?", (cursor.lastrowid,))

    def tag_version(self, tag_name_or_id: str | int, version_id: str) -> bool:
        """Associate a tag with a version.

        Parameters
        ----------
        tag_name_or_id : str or int
            Tag name (str) or tag id (int).
        version_id : str
            The version to tag.

        Returns
        -------
        bool
            ``True`` if the association was created, ``False`` if it already
            existed or the tag/version was not found.
        """
        tag = self._resolve_tag(tag_name_or_id)
        if tag is None:
            return False
        ver = self.get_version(version_id)
        if ver is None:
            return False

        try:
            self.conn.execute(
                "INSERT INTO version_tags (version_id, tag_id) VALUES (?, ?)",
                (version_id, tag["id"]),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_version_tags(self, version_id: str) -> list[dict | sqlite3.Row]:
        """Return all tags associated with a version.

        Parameters
        ----------
        version_id : str
            The version to query.

        Returns
        -------
        list[dict or sqlite3.Row]
            The tag records.
        """
        return self._all_rows(
            """SELECT t.* FROM tags t
               JOIN version_tags vt ON vt.tag_id = t.id
               WHERE vt.version_id = ?
               ORDER BY t.name""",
            (version_id,),
        )

    def get_related_tags(self, tag_name_or_id: str | int) -> list[dict | sqlite3.Row]:
        """Return all tags related to a given tag via ``tag_relations``.

        Parameters
        ----------
        tag_name_or_id : str or int
            Tag name (str) or tag id (int).

        Returns
        -------
        list[dict or sqlite3.Row]
            The related tag records, each augmented with a ``relation`` key.
        """
        tag = self._resolve_tag(tag_name_or_id)
        if tag is None:
            return []

        rows = self._all_rows(
            """SELECT t.*, tr.relation
               FROM tag_relations tr
               JOIN tags t ON t.id = tr.tag2_id
               WHERE tr.tag1_id = ?
               UNION
               SELECT t.*, tr.relation
               FROM tag_relations tr
               JOIN tags t ON t.id = tr.tag1_id
               WHERE tr.tag2_id = ?""",
            (tag["id"], tag["id"]),
        )
        return rows

    def add_tag_relation(
        self,
        tag1_name_or_id: str | int,
        tag2_name_or_id: str | int,
        relation: str,
    ) -> bool:
        """Record a relation between two tags.

        Parameters
        ----------
        tag1_name_or_id : str or int
        tag2_name_or_id : str or int
        relation : str
            Relation type (e.g. ``"broader"``, ``"narrower"``, ``"related"``,
            ``"conflicts"``).

        Returns
        -------
        bool
            ``True`` if created, ``False`` if it already existed or tags not found.
        """
        tag1 = self._resolve_tag(tag1_name_or_id)
        tag2 = self._resolve_tag(tag2_name_or_id)
        if tag1 is None or tag2 is None:
            return False
        try:
            self.conn.execute(
                "INSERT INTO tag_relations (tag1_id, tag2_id, relation) VALUES (?, ?, ?)",
                (tag1["id"], tag2["id"], relation),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def _resolve_tag(self, name_or_id: str | int) -> Optional[dict | sqlite3.Row]:
        """Resolve a tag name (str) or id (int) to its row."""
        if isinstance(name_or_id, int):
            return self._row("SELECT * FROM tags WHERE id = ?", (name_or_id,))
        return self._row("SELECT * FROM tags WHERE name = ?", (name_or_id,))

    # ---- agent work -------------------------------------------------------

    def record_work(
        self,
        version_id: str,
        agent_type: str,
        *,
        input_spec: Optional[str] = None,
        output_log: Optional[str] = None,
        exit_status: str = "ok",
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> dict | sqlite3.Row:
        """Record agent work for a version.

        Parameters
        ----------
        version_id : str
            The version the agent worked on.
        agent_type : str
            Agent type (e.g. ``"builder"``, ``"creator"``, ``"validator"``).
        input_spec : str, optional
            What the agent was asked to do.
        output_log : str, optional
            What the agent produced / summary.
        exit_status : str, optional
            ``"ok"`` (default), ``"failed"``, or ``"skipped"``.
        started_at : str, optional
            ISO datetime when work started.
        finished_at : str, optional
            ISO datetime when work finished.

        Returns
        -------
        dict or sqlite3.Row
            The newly inserted agent_work record.
        """
        if not agent_type.strip():
            raise ValueError("agent_type must not be empty")

        ver = self.get_version(version_id)
        if ver is None:
            raise ValueError(f"Version {version_id!r} does not exist")

        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO agent_work
               (version_id, agent_type, input_spec, output_log, exit_status, started_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (version_id, agent_type, input_spec, output_log, exit_status,
             started_at or now, finished_at),
        )
        self.conn.commit()
        return self._row("SELECT * FROM agent_work WHERE id = ?", (cursor.lastrowid,))

    def get_version_work(self, version_id: str) -> list[dict | sqlite3.Row]:
        """Return all agent work records for a version, ordered by id.

        Parameters
        ----------
        version_id : str
            The version to query.

        Returns
        -------
        list[dict or sqlite3.Row]
            The agent_work records.
        """
        return self._all_rows(
            "SELECT * FROM agent_work WHERE version_id = ? ORDER BY id",
            (version_id,),
        )


# ---- symlink helper -------------------------------------------------------

def _update_symlink(link_path: str, target: str) -> None:
    """Create or atomically replace a symlink."""
    temp = link_path + ".tmp"
    try:
        os.symlink(target, temp)
    except FileExistsError:
        os.unlink(temp)
        os.symlink(target, temp)
    os.replace(temp, link_path)
