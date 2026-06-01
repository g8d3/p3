Now I have the full schema. Let me implement the module and tests.
The `dict` row factory can't be used directly — SQLite's cursor expects a callable `(cursor, row) -> dict`. Let me fix that.
Two issues: the `_next_version_id` function needs `row["id"]` since rows are dicts with the row factory, and the symlink test and schema test need minor fixes.
Now fix the two test issues:
The issue is the `return` before the `last` assignment — it's dead code. Let me read the current state and fix.
All 61 tests pass. Let me clean up any artifacts from the test run.
Done. Here's what was implemented:

**`version_registry.py`** — SQLite-backed `VersionRegistry` class with:

| Method | Purpose |
|---|---|
| `create_version()` | Auto-incrementing v001/v002/... IDs, creates filesystem dir |
| `get_version()` | Fetch by ID (returns `None` if missing) |
| `list_versions()` | Optional filter by status, ASC/DESC order |
| `update_version()` | Update columns (`parent_id`, `status`, `message`, etc.) |
| `set_live()` / `get_live()` | Single-live-version enforcement + symlink management |
| `create_tag()` / `tag_version()` | Tags with unique names, associate with versions |
| `get_version_tags()` / `get_related_tags()` | Query tags and tag_relations |
| `add_tag_relation()` | Record broader/narrower/related/conflicts |
| `record_work()` / `get_version_work()` | Agent work metadata per version |

All 5 tables from SCHEMA.md are created automatically, with the partial unique index on `live WHERE live = 1`, WAL mode, and foreign keys enabled. Zero external dependencies (stdlib only).

**`test_version_registry.py`** — 61 tests across 16 test classes, all passing.
