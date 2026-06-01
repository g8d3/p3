Let me run the tests first to see the current state.
All 61 tests pass. Now let me check for any existing artifacts and plan the edge case tests.
First, clean up the leftover version directories from previous test runs.
Now I'll add all the edge case tests. Let me make the edits in parallel since they're in different parts of the file.
All 67 tests pass — the 6 new edge case tests all in green. Now let me check coverage.
## Summary

### 1. Execution
```bash
uv run --with pytest python3 -m pytest test_version_registry.py -v
```

### 2. Tests: 67 passed (was 61), 0 failures
No fixes needed in `version_registry.py` — all original tests passed.

### 3. Edge case tests added (6 new)

| Category | Test | What it covers |
|---|---|---|
| Empty DB | `test_empty_db_with_status` | `list_versions(status="draft")` on empty DB |
| Empty DB | `test_non_existent_version` (GetVersionTags) | `get_version_tags("v999")` on non-existent version |
| Empty DB | `test_non_existent_version` (GetVersionWork) | `get_version_work("v999")` on non-existent version |
| Duplicate tags | `test_reverse_direction` | `add_tag_relation("b","a")` after `add_tag_relation("a","b")` — different PK, should succeed |
| Set live twice | `test_set_same_version_live_twice` | `set_live("v001")` called twice on the same version (idempotency) |
| 100 versions | `test_list_100_versions` | Creates 100 versions, verifies count and DESC order |

### 4. Coverage: 99%
```
Name                       Stmts   Miss  Cover
version_registry.py          162      4    98%
test_version_registry.py     333      0   100%
```
The 4 uncovered lines (34, 565–567) are defensive code paths that require corrupted DB state or race conditions — not reachable through normal operations.

### 5. Design Issues

**🔴 `list_versions` doesn't validate the `order` parameter** — it's interpolated directly into SQL (`ORDER BY id ` + order). Passing `order="ASC; DROP TABLE versions"` would work. Should validate against `{"ASC", "DESC"}` or use parameterized ordering.

**🔴 Version ID sorting breaks at 1000+ versions** — IDs like `v001`–`v999` sort correctly with string ordering (zero-padded), but `v1000` < `v999` lexicographically. `_next_version_id` uses `:03d` padding, so version 1000 becomes `v1000` (4 chars) which sorts before `v999`. Fix: use wider padding (`:06d`) or order by `CAST(substr(id,2) AS INTEGER)`.

**🟡 `update_version` doesn't validate fields** — `create_version` rejects empty `created_by`/`message`, but `update_version` accepts them without validation, allowing corruption of previously valid records.

**🟡 Orphan directories on SQL failure** — If `create_version`'s INSERT fails (e.g., constraint), the `os.makedirs(ver_path)` leaves an empty directory with no cleanup.

**🟡 `_VERSIONS_DIR` and `_LIVE_SYMLINK` are module-level globals** — All `VersionRegistry` instances share the same filesystem paths, preventing multiple registries from coexisting in the same Python process.

**🟡 `_update_symlink` has a race on the `.tmp` file** — If `link_path + ".tmp"` is a directory, `os.unlink` crashes with `IsADirectoryError` instead of falling through properly.

**⚪ No context manager support** — `VersionRegistry` requires explicit `.close()`. Adding `__enter__`/`__exit__` would be more Pythonic.
