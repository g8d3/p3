"""SQLite database for historical subnet data."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from subnet_trader.models import SubnetData

DEFAULT_DB_PATH = Path(__file__).parent.parent / "subnet_history.db"


class HistoryDB:
    """SQLite storage for subnet snapshots and historical data."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    block_number INTEGER,
                    netuid INTEGER NOT NULL,
                    name TEXT,
                    tao_staked REAL,
                    alpha_price REAL,
                    tao_reserve REAL,
                    alpha_reserve REAL,
                    emission_share REAL,
                    tao_emission_per_block REAL,
                    volume_24h REAL,
                    price_change_1d REAL,
                    price_change_7d REAL,
                    raw_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_netuid_ts
                ON snapshots (netuid, timestamp)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save_snapshot(self, subnets: list[SubnetData], block_number: int | None = None):
        """Save a snapshot of all subnet data."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for s in subnets:
                conn.execute("""
                    INSERT INTO snapshots (
                        timestamp, block_number, netuid, name,
                        tao_staked, alpha_price, tao_reserve, alpha_reserve,
                        emission_share, tao_emission_per_block,
                        volume_24h, price_change_1d, price_change_7d, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now, block_number, s.netuid, s.name,
                    s.tao_staked, s.alpha_price, s.tao_reserve, s.alpha_reserve,
                    s.emission_share, s.tao_emission_per_block,
                    s.volume_24h, s.price_change_1d, s.price_change_7d,
                    json.dumps(s.to_dict()),
                ))
            conn.commit()

    def get_emission_history(self, days: int = 7) -> dict[int, float]:
        """Get emission share from ~7 days ago for each subnet.

        Returns dict mapping netuid → emission_share from oldest snapshot
        within the time window.
        """
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT netuid, emission_share
                FROM snapshots
                WHERE timestamp <= datetime('now', ?)
                GROUP BY netuid
                HAVING timestamp = MIN(timestamp)
            """, (f"-{days} days",)).fetchall()

        return {row["netuid"]: row["emission_share"] for row in rows}

    def get_price_ma(self, days: int = 30) -> dict[int, float]:
        """Get 30-day moving average of alpha price for each subnet.

        Returns dict mapping netuid → average price.
        """
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT netuid, AVG(alpha_price) as avg_price
                FROM snapshots
                WHERE timestamp >= datetime('now', ?)
                GROUP BY netuid
            """, (f"-{days} days",)).fetchall()

        return {row["netuid"]: row["avg_price"] for row in rows if row["avg_price"] is not None}

    def get_latest_snapshot(self) -> list[dict]:
        """Get the most recent snapshot for all subnets."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT raw_json
                FROM snapshots
                WHERE timestamp = (SELECT MAX(timestamp) FROM snapshots)
            """).fetchall()

        return [json.loads(row["raw_json"]) for row in rows]

    def prune_old_data(self, keep_days: int = 90):
        """Remove snapshots older than keep_days."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM snapshots WHERE timestamp < datetime('now', ?)",
                (f"-{keep_days} days",)
            )
            conn.commit()
