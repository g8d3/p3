"""Tests for version_registry.py."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from version_registry import VersionRegistry, _next_version_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path() -> str:
    """Return a path to a temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def reg(db_path: str) -> VersionRegistry:
    """Return a VersionRegistry backed by a temporary database."""
    r = VersionRegistry(db_path)
    yield r
    r.close()


# ---------------------------------------------------------------------------
# _next_version_id
# ---------------------------------------------------------------------------

class TestNextVersionId:
    def test_empty_db(self, reg: VersionRegistry) -> None:
        assert _next_version_id(reg.conn.cursor()) == "v001"

    def test_increments(self, reg: VersionRegistry) -> None:
        reg.create_version("test", "first")
        assert _next_version_id(reg.conn.cursor()) == "v002"

    def test_three_digit_padding(self, reg: VersionRegistry) -> None:
        for _ in range(999):
            reg.create_version("test", "seed")
        assert _next_version_id(reg.conn.cursor()) == "v1000"


# ---------------------------------------------------------------------------
# create_version
# ---------------------------------------------------------------------------

class TestCreateVersion:
    def test_basic_creation(self, reg: VersionRegistry) -> None:
        v = reg.create_version("human", "Initial commit")
        assert v["id"] == "v001"
        assert v["created_by"] == "human"
        assert v["message"] == "Initial commit"
        assert v["status"] == "draft"
        assert v["live"] == 0
        assert v["parent_id"] is None
        assert Path(v["path"]).name == "v001"

    def test_auto_increment(self, reg: VersionRegistry) -> None:
        v1 = reg.create_version("builder", "first")
        v2 = reg.create_version("builder", "second")
        assert v1["id"] == "v001"
        assert v2["id"] == "v002"

    def test_with_parent(self, reg: VersionRegistry) -> None:
        parent = reg.create_version("human", "parent")
        child = reg.create_version("builder", "fork", parent_id=parent["id"])
        assert child["parent_id"] == parent["id"]

    def test_custom_status(self, reg: VersionRegistry) -> None:
        v = reg.create_version("human", "test", status="active")
        assert v["status"] == "active"

    def test_created_at_set(self, reg: VersionRegistry) -> None:
        v = reg.create_version("human", "test")
        assert v["created_at"] is not None
        assert len(v["created_at"]) > 0

    def test_empty_created_by_raises(self, reg: VersionRegistry) -> None:
        with pytest.raises(ValueError, match="created_by"):
            reg.create_version("", "msg")

    def test_empty_message_raises(self, reg: VersionRegistry) -> None:
        with pytest.raises(ValueError, match="message"):
            reg.create_version("human", "")

    def test_creates_directory(self, reg: VersionRegistry) -> None:
        v = reg.create_version("human", "test")
        assert os.path.isdir(v["path"])


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------

class TestGetVersion:
    def test_returns_version(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "hello")
        v = reg.get_version("v001")
        assert v is not None
        assert v["id"] == "v001"

    def test_returns_none_for_missing(self, reg: VersionRegistry) -> None:
        assert reg.get_version("v999") is None

    def test_returns_none_for_empty_db(self, reg: VersionRegistry) -> None:
        assert reg.get_version("v001") is None


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------

class TestListVersions:
    def test_empty(self, reg: VersionRegistry) -> None:
        assert reg.list_versions() == []

    def test_returns_all(self, reg: VersionRegistry) -> None:
        reg.create_version("a", "first")
        reg.create_version("b", "second")
        reg.create_version("c", "third")
        versions = reg.list_versions()
        assert len(versions) == 3
        assert [v["id"] for v in versions] == ["v003", "v002", "v001"]

    def test_ascending_order(self, reg: VersionRegistry) -> None:
        reg.create_version("a", "first")
        reg.create_version("b", "second")
        versions = reg.list_versions(order="ASC")
        assert [v["id"] for v in versions] == ["v001", "v002"]

    def test_filter_by_status(self, reg: VersionRegistry) -> None:
        reg.create_version("a", "first", status="active")
        reg.create_version("b", "second", status="draft")
        reg.create_version("c", "third", status="archived")
        active = reg.list_versions(status="active")
        assert len(active) == 1
        assert active[0]["id"] == "v001"

    def test_empty_db_with_status(self, reg: VersionRegistry) -> None:
        assert reg.list_versions(status="draft") == []

    def test_list_100_versions(self, reg: VersionRegistry) -> None:
        for i in range(100):
            reg.create_version("human", f"version {i}")
        versions = reg.list_versions()
        assert len(versions) == 100
        ids = [v["id"] for v in versions]
        assert ids == [f"v{i:03d}" for i in range(100, 0, -1)]


# ---------------------------------------------------------------------------
# update_version
# ---------------------------------------------------------------------------

class TestUpdateVersion:
    def test_update_status(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        v = reg.update_version("v001", status="active")
        assert v["status"] == "active"

    def test_update_message(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "original")
        v = reg.update_version("v001", message="updated msg")
        assert v["message"] == "updated msg"

    def test_update_multiple(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        v = reg.update_version("v001", message="new", status="active")
        assert v["message"] == "new"
        assert v["status"] == "active"

    def test_missing_version(self, reg: VersionRegistry) -> None:
        assert reg.update_version("v999", status="active") is None

    def test_unknown_field_raises(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        with pytest.raises(ValueError, match="Unknown"):
            reg.update_version("v001", bogus="x")

    def test_no_fields_raises(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        with pytest.raises(ValueError, match="least one field"):
            reg.update_version("v001")


# ---------------------------------------------------------------------------
# set_live / get_live
# ---------------------------------------------------------------------------

class TestLive:
    def test_set_live(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "first")
        v = reg.set_live("v001")
        assert v is not None
        assert v["live"] == 1
        assert reg.get_live()["id"] == "v001"

    def test_only_one_live(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "first")
        reg.create_version("human", "second")
        reg.set_live("v001")
        reg.set_live("v002")
        live = reg.get_live()
        assert live["id"] == "v002"
        assert reg.get_version("v001")["live"] == 0

    def test_set_live_missing(self, reg: VersionRegistry) -> None:
        assert reg.set_live("v999") is None

    def test_get_live_none(self, reg: VersionRegistry) -> None:
        assert reg.get_live() is None

    def test_set_same_version_live_twice(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        v1 = reg.set_live("v001")
        assert v1 is not None
        assert v1["live"] == 1
        v2 = reg.set_live("v001")
        assert v2 is not None
        assert v2["live"] == 1
        assert reg.get_live()["id"] == "v001"

    def test_symlink_created(self, reg: VersionRegistry, db_path: str) -> None:
        reg.create_version("human", "test")
        reg.set_live("v001")
        # symlink lives next to the module (project dir), not next to db
        from version_registry import _LIVE_SYMLINK
        assert os.path.islink(_LIVE_SYMLINK)
        assert os.path.realpath(_LIVE_SYMLINK).endswith("versions/v001")
        os.unlink(_LIVE_SYMLINK)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TestCreateTag:
    def test_basic(self, reg: VersionRegistry) -> None:
        t = reg.create_tag("ui", "human")
        assert t["name"] == "ui"
        assert t["created_by"] == "human"
        assert isinstance(t["id"], int)

    def test_duplicate_name_raises(self, reg: VersionRegistry) -> None:
        reg.create_tag("ui", "human")
        with pytest.raises(sqlite3.IntegrityError):
            reg.create_tag("ui", "builder")

    def test_empty_name_raises(self, reg: VersionRegistry) -> None:
        with pytest.raises(ValueError, match="tag name"):
            reg.create_tag("", "human")

    def test_empty_created_by_raises(self, reg: VersionRegistry) -> None:
        with pytest.raises(ValueError, match="created_by"):
            reg.create_tag("ui", "")


class TestTagVersion:
    def test_tag_a_version(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        reg.create_tag("ui", "human")
        assert reg.tag_version("ui", "v001") is True

    def test_tag_by_id(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        t = reg.create_tag("ui", "human")
        assert reg.tag_version(t["id"], "v001") is True

    def test_duplicate_tag_version(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        reg.create_tag("ui", "human")
        reg.tag_version("ui", "v001")
        assert reg.tag_version("ui", "v001") is False  # already exists

    def test_missing_tag(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        assert reg.tag_version("nonexistent", "v001") is False

    def test_missing_version(self, reg: VersionRegistry) -> None:
        reg.create_tag("ui", "human")
        assert reg.tag_version("ui", "v999") is False


class TestGetVersionTags:
    def test_no_tags(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        assert reg.get_version_tags("v001") == []

    def test_returns_tags(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        reg.create_tag("ui", "human")
        reg.create_tag("bugfix", "builder")
        reg.tag_version("ui", "v001")
        reg.tag_version("bugfix", "v001")
        tags = reg.get_version_tags("v001")
        assert len(tags) == 2
        names = {t["name"] for t in tags}
        assert names == {"ui", "bugfix"}

    def test_multiple_versions(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "a")
        reg.create_version("human", "b")
        reg.create_tag("ui", "human")
        reg.tag_version("ui", "v001")
        assert len(reg.get_version_tags("v002")) == 0

    def test_non_existent_version(self, reg: VersionRegistry) -> None:
        assert reg.get_version_tags("v999") == []


class TestGetRelatedTags:
    def test_no_relations(self, reg: VersionRegistry) -> None:
        reg.create_tag("ui", "human")
        assert reg.get_related_tags("ui") == []

    def test_directional(self, reg: VersionRegistry) -> None:
        reg.create_tag("ui", "human")
        reg.create_tag("frontend", "human")
        reg.add_tag_relation("ui", "frontend", "narrower")
        related = reg.get_related_tags("ui")
        assert len(related) == 1
        assert related[0]["name"] == "frontend"
        assert related[0]["relation"] == "narrower"

    def test_undirectional(self, reg: VersionRegistry) -> None:
        reg.create_tag("a", "human")
        reg.create_tag("b", "human")
        reg.add_tag_relation("a", "b", "related")
        # Both directions should be found
        assert len(reg.get_related_tags("a")) == 1
        assert len(reg.get_related_tags("b")) == 1

    def test_missing_tag(self, reg: VersionRegistry) -> None:
        assert reg.get_related_tags("nonexistent") == []


class TestAddTagRelation:
    def test_basic(self, reg: VersionRegistry) -> None:
        reg.create_tag("a", "h")
        reg.create_tag("b", "h")
        assert reg.add_tag_relation("a", "b", "related") is True

    def test_duplicate_raises(self, reg: VersionRegistry) -> None:
        reg.create_tag("a", "h")
        reg.create_tag("b", "h")
        reg.add_tag_relation("a", "b", "related")
        assert reg.add_tag_relation("a", "b", "related") is False

    def test_missing_tag1(self, reg: VersionRegistry) -> None:
        reg.create_tag("b", "h")
        assert reg.add_tag_relation("nonexistent", "b", "related") is False

    def test_missing_tag2(self, reg: VersionRegistry) -> None:
        reg.create_tag("a", "h")
        assert reg.add_tag_relation("a", "nonexistent", "related") is False

    def test_reverse_direction(self, reg: VersionRegistry) -> None:
        reg.create_tag("a", "h")
        reg.create_tag("b", "h")
        reg.add_tag_relation("a", "b", "related")
        assert reg.add_tag_relation("b", "a", "related") is True


# ---------------------------------------------------------------------------
# Agent Work
# ---------------------------------------------------------------------------

class TestRecordWork:
    def test_basic(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        w = reg.record_work("v001", "builder", input_spec="build app")
        assert w["version_id"] == "v001"
        assert w["agent_type"] == "builder"
        assert w["input_spec"] == "build app"
        assert w["output_log"] is None
        assert w["exit_status"] == "ok"
        assert w["id"] == 1

    def test_with_all_fields(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        w = reg.record_work(
            "v001",
            "validator",
            input_spec="check logic",
            output_log="all good",
            exit_status="ok",
            started_at="2025-01-01 00:00:00",
            finished_at="2025-01-01 01:00:00",
        )
        assert w["output_log"] == "all good"
        assert w["started_at"] == "2025-01-01 00:00:00"
        assert w["finished_at"] == "2025-01-01 01:00:00"

    def test_default_started_at(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        w = reg.record_work("v001", "builder")
        assert w["started_at"] is not None

    def test_missing_version_raises(self, reg: VersionRegistry) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            reg.record_work("v999", "builder")

    def test_empty_agent_type_raises(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        with pytest.raises(ValueError, match="agent_type"):
            reg.record_work("v001", "")


class TestGetVersionWork:
    def test_no_work(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        assert reg.get_version_work("v001") == []

    def test_multiple_records(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "test")
        reg.record_work("v001", "builder", input_spec="build")
        reg.record_work("v001", "validator", input_spec="validate")
        reg.record_work("v001", "creator", input_spec="create")
        records = reg.get_version_work("v001")
        assert len(records) == 3
        assert [r["agent_type"] for r in records] == ["builder", "validator", "creator"]

    def test_other_version_not_included(self, reg: VersionRegistry) -> None:
        reg.create_version("human", "a")
        reg.create_version("human", "b")
        reg.record_work("v001", "builder")
        assert len(reg.get_version_work("v002")) == 0

    def test_non_existent_version(self, reg: VersionRegistry) -> None:
        assert reg.get_version_work("v999") == []


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

class TestConnection:
    def test_close(self, db_path: str) -> None:
        r = VersionRegistry(db_path)
        r.create_version("human", "test")
        r.close()
        # Should be able to reconnect
        r2 = VersionRegistry(db_path)
        assert r2.get_version("v001") is not None
        r2.close()


# ---------------------------------------------------------------------------
# Row factory
# ---------------------------------------------------------------------------

class TestRowFactory:
    def test_dict_factory_default(self, db_path: str) -> None:
        r = VersionRegistry(db_path)
        v = r.create_version("human", "test")
        assert isinstance(v, dict)
        r.close()

    def test_sqlite3_row_factory(self, db_path: str) -> None:
        r = VersionRegistry(db_path, row_factory=sqlite3.Row)
        v = r.create_version("human", "test")
        assert isinstance(v, sqlite3.Row)
        r.close()


# ---------------------------------------------------------------------------
# Schema is initialised on connect
# ---------------------------------------------------------------------------

class TestSchemaInit:
    def test_tables_exist(self, db_path: str) -> None:
        r = VersionRegistry(db_path)
        cursor = r.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        tables -= {"sqlite_sequence"}  # internal AUTOINCREMENT tracking table
        assert tables == {"agent_work", "tag_relations", "version_tags", "versions", "tags"}
        r.close()
