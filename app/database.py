"""Small SQLite event store. SQL queries use bound parameters."""
import sqlite3
from contextlib import closing
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
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    event TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_security_events_ip_time ON security_events(client_ip,created_at);
CREATE TRIGGER IF NOT EXISTS access_logs_no_update BEFORE UPDATE ON access_logs
BEGIN SELECT RAISE(ABORT, 'access_logs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS access_logs_no_delete BEFORE DELETE ON access_logs
BEGIN SELECT RAISE(ABORT, 'access_logs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS security_events_no_update BEFORE UPDATE ON security_events
BEGIN SELECT RAISE(ABORT, 'security_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS security_events_no_delete BEFORE DELETE ON security_events
BEGIN SELECT RAISE(ABORT, 'security_events is append-only'); END;
'''


def connect(db_path: Path):
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: Path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as con, con:
        con.executescript(DDL)


def insert_log(db_path, ip, path, score, ml_label, action, status, reason, duration_ms):
    with closing(connect(db_path)) as con, con:
        con.execute('''INSERT INTO access_logs
            (created_at, client_ip, requested_path, ml_score, ml_label,
             action, http_status, reason, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now(timezone.utc).isoformat(timespec='seconds'), ip,
             path[:4096], score, ml_label, action, status, reason, duration_ms))


def recent_logs(db_path, limit=100, action=None):
    if action is not None and action not in {'ALLOW', 'BLOCK', 'MISS'}:
        raise ValueError('Invalid action filter')
    with closing(connect(db_path)) as con, con:
        query = 'SELECT * FROM access_logs'
        params = []
        if action:
            query += ' WHERE action=?'
            params.append(action)
        query += ' ORDER BY id DESC LIMIT ?'
        params.append(max(1, min(int(limit), 500)))
        return [dict(x) for x in con.execute(query, params)]


def insert_security_event(db_path, ip, role, event):
    with closing(connect(db_path)) as con, con:
        con.execute('INSERT INTO security_events(created_at,client_ip,actor_role,event) VALUES (?,?,?,?)',
                    (datetime.now(timezone.utc).isoformat(timespec='seconds'), ip, role, event))


def failed_login_count(db_path, ip, since):
    with closing(connect(db_path)) as con:
        return con.execute("SELECT COUNT(*) FROM security_events WHERE client_ip=? AND event='login_failed' AND created_at>=?",
                           (ip, since)).fetchone()[0]


def recent_security_events(db_path):
    with closing(connect(db_path)) as con:
        return [dict(r) for r in con.execute('SELECT * FROM security_events ORDER BY id DESC LIMIT 30')]


def summary(db_path):
    with closing(connect(db_path)) as con, con:
        return dict(con.execute('''SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN action='BLOCK' THEN 1 ELSE 0 END) AS blocked,
            SUM(CASE WHEN action='ALLOW' THEN 1 ELSE 0 END) AS allowed,
            SUM(CASE WHEN ml_label='suspicious' THEN 1 ELSE 0 END) AS suspicious
            FROM access_logs''').fetchone())
