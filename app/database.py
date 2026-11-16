"""Small SQLite event store. SQL queries use bound parameters."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DDL = '''
CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    requested_path TEXT NOT NULL,
    ml_score REAL,
    ml_label TEXT NOT NULL,
    action TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    reason TEXT NOT NULL,
    duration_ms REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_access_logs_created ON access_logs(created_at);
'''


def connect(db_path: Path):
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: Path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as con:
        con.executescript(DDL)


def insert_log(db_path, ip, path, score, ml_label, action, status, reason, duration_ms):
    with connect(db_path) as con:
        con.execute('''INSERT INTO access_logs
            (created_at, client_ip, requested_path, ml_score, ml_label,
             action, http_status, reason, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now(timezone.utc).isoformat(timespec='seconds'), ip,
             path[:4096], score, ml_label, action, status, reason, duration_ms))


def recent_logs(db_path, limit=100):
    with connect(db_path) as con:
        return [dict(x) for x in con.execute(
            'SELECT * FROM access_logs ORDER BY id DESC LIMIT ?', (min(int(limit), 500),))]


def summary(db_path):
    with connect(db_path) as con:
        return dict(con.execute('''SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN action='BLOCK' THEN 1 ELSE 0 END) AS blocked,
            SUM(CASE WHEN action='ALLOW' THEN 1 ELSE 0 END) AS allowed,
            SUM(CASE WHEN ml_label='suspicious' THEN 1 ELSE 0 END) AS suspicious
            FROM access_logs''').fetchone())
