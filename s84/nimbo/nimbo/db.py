import sqlite3
import json
from pathlib import Path


class _Engine:
    def connect(self, url): raise NotImplementedError
    def create(self, table, data): raise NotImplementedError
    def read(self, table, id): raise NotImplementedError
    def update(self, table, id, data): raise NotImplementedError
    def delete(self, table, id): raise NotImplementedError
    def list(self, table, filters=None): raise NotImplementedError
    def migrate(self, schema): raise NotImplementedError
    def close(self): raise NotImplementedError


class _SQLite(_Engine):
    def __init__(self):
        self._conn = None

    def connect(self, url):
        path = url.replace("sqlite:///", "")
        if path == ":memory:":
            self._conn = sqlite3.connect(":memory:")
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        if path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self

    def _row_to_dict(self, row):
        if row is None: return None
        return dict(row)

    def create(self, table, data):
        cols = ", ".join(data.keys())
        vals = ", ".join("?" for _ in data)
        cur = self._conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})",
                                 list(data.values()))
        self._conn.commit()
        return self.read(table, cur.lastrowid)

    def read(self, table, id):
        cur = self._conn.execute(f"SELECT * FROM {table} WHERE id=?", (id,))
        return self._row_to_dict(cur.fetchone())

    def update(self, table, id, data):
        sets = ", ".join(f"{k}=?" for k in data)
        self._conn.execute(f"UPDATE {table} SET {sets} WHERE id=?",
                           list(data.values()) + [id])
        self._conn.commit()
        return self.read(table, id)

    def delete(self, table, id):
        old = self.read(table, id)
        self._conn.execute(f"DELETE FROM {table} WHERE id=?", (id,))
        self._conn.commit()
        return old

    def list(self, table, filters=None):
        if filters:
            where = " AND ".join(f"{k}=?" for k in filters)
            cur = self._conn.execute(f"SELECT * FROM {table} WHERE {where}",
                                     list(filters.values()))
        else:
            cur = self._conn.execute(f"SELECT * FROM {table}")
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def migrate(self, schema):
        for name, fields in schema.items():
            cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for f in fields:
                typ = "TEXT"
                if f.get("type") in ("int", "integer"): typ = "INTEGER"
                if f.get("type") == "float": typ = "REAL"
                if f.get("type") == "bool": typ = "INTEGER"
                extra = " DEFAULT 1" if f.get("default") is True else ""
                extra = " DEFAULT 0" if f.get("default") is False else extra
                if f.get("default") is not None and f.get("default") not in (True, False):
                    extra = f" DEFAULT '{f['default']}'"
                cols.append(f"{f['name']} {typ}{extra}")
            self._conn.execute(f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(cols)})")
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()


class Database:
    engines = {"sqlite": _SQLite}

    def __init__(self, url):
        self.url = url
        self.engine = None
        for prefix, cls in self.engines.items():
            if url.startswith(f"{prefix}://"):
                self.engine = cls().connect(url)
                break
        if not self.engine:
            raise ValueError(f"Unsupported DB engine in: {url}")

    @classmethod
    def register_engine(cls, prefix, engine_cls):
        cls.engines[prefix] = engine_cls

    def create(self, table, data):
        return self.engine.create(table, data)

    def read(self, table, id):
        return self.engine.read(table, id)

    def update(self, table, id, data):
        return self.engine.update(table, id, data)

    def delete(self, table, id):
        return self.engine.delete(table, id)

    def list(self, table, filters=None):
        return self.engine.list(table, filters)

    def migrate(self, schema):
        self.engine.migrate(schema)

    def close(self):
        self.engine.close()


class DBPool:
    def __init__(self):
        self._dbs = {}

    def add(self, name, url):
        self._dbs[name] = Database(url)
        return self._dbs[name]

    def get(self, name="default"):
        return self._dbs.get(name)

    def __getitem__(self, name):
        return self._dbs[name]

    def keys(self):
        return self._dbs.keys()

    def items(self):
        return self._dbs.items()

    def migrate_all(self, models_by_db):
        for name, schema in models_by_db.items():
            db = self._dbs.get(name)
            if db:
                db.migrate(schema)

    def close_all(self):
        for db in self._dbs.values():
            db.close()
