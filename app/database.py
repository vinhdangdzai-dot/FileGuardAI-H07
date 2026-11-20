"""Small SQLite event store. SQL queries use bound parameters."""
import sqlite3
import math
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from .log_filters import LABELS, where_clause
from .alerts import DDL as ALERT_DDL, record as record_alert

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
CREATE TABLE IF NOT EXISTS download_context (
 event_id INTEGER PRIMARY KEY REFERENCES access_logs(id),
 path_outcome TEXT NOT NULL CHECK(path_outcome IN ('permitted','rejected','missing')),
 visibility TEXT NOT NULL CHECK(visibility IN ('public','authenticated','unknown')),
 access_outcome TEXT NOT NULL CHECK(access_outcome IN ('allowed','login_required','not_applicable')));
CREATE TABLE IF NOT EXISTS processing_timings (
 event_id INTEGER PRIMARY KEY REFERENCES access_logs(id),
 ids_ms REAL NOT NULL CHECK(ids_ms >= 0),
 ips_ms REAL NOT NULL CHECK(ips_ms >= 0),
 total_ms REAL NOT NULL CHECK(total_ms >= 0));
CREATE TRIGGER IF NOT EXISTS processing_timings_no_update BEFORE UPDATE ON processing_timings
BEGIN SELECT RAISE(ABORT, 'processing_timings is append-only'); END;
CREATE TRIGGER IF NOT EXISTS processing_timings_no_delete BEFORE DELETE ON processing_timings
BEGIN SELECT RAISE(ABORT, 'processing_timings is append-only'); END;
CREATE TRIGGER IF NOT EXISTS download_context_no_update BEFORE UPDATE ON download_context
BEGIN SELECT RAISE(ABORT, 'download_context is append-only'); END;
CREATE TRIGGER IF NOT EXISTS download_context_no_delete BEFORE DELETE ON download_context
BEGIN SELECT RAISE(ABORT, 'download_context is append-only'); END;
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
        con.executescript(ALERT_DDL)
    from .account_store import migrate
    migrate(db_path)


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def insert_log(db_path, ip, path, score, ml_label, action, status, reason, duration_ms, *, context=None, timing=None):
    if not all(isinstance(x, str) for x in (ip, path, ml_label, action, reason)) or not ip or not reason:
        raise ValueError('Invalid log text fields')
    if ml_label not in LABELS or {'ALLOW': 200, 'BLOCK': 403, 'MISS': 404}.get(action) != status or type(status) is not int:
        raise ValueError('Invalid log label/action/status')
    if score is not None and (not _finite_number(score) or not 0 <= score <= 1):
        raise ValueError('Invalid probability in log')
    if not _finite_number(duration_ms) or duration_ms < 0:
        raise ValueError('Invalid duration in log')
    if context is not None and (not isinstance(context,dict) or set(context)!={'path_outcome','visibility','access_outcome'}
            or context['path_outcome'] not in {'permitted','rejected','missing'}
            or context['visibility'] not in {'public','authenticated','unknown'}
            or context['access_outcome'] not in {'allowed','login_required','not_applicable'}):
        raise ValueError('Invalid download context')
    if context is not None:
        if ((context['path_outcome']=='rejected' and action!='BLOCK')
                or (action=='MISS' and context['path_outcome']!='missing')
                or (action=='ALLOW' and (context['path_outcome']!='permitted' or context['access_outcome']!='allowed'))
                or (context['access_outcome']=='login_required' and
                    (action!='BLOCK' or context['path_outcome']!='permitted' or context['visibility']!='authenticated'))):
            raise ValueError('Inconsistent download context')
    if timing is not None:
        if (not isinstance(timing, dict) or set(timing) != {'ids_ms', 'ips_ms', 'total_ms'}
                or any(not _finite_number(timing[key]) or timing[key] < 0 for key in timing)
                or timing['total_ms'] + 1e-9 < timing['ids_ms'] + timing['ips_ms']):
            raise ValueError('Invalid processing timing')
    with closing(connect(db_path)) as con, con:
        cursor = con.execute('''INSERT INTO access_logs
            (created_at, client_ip, requested_path, ml_score, ml_label,
             action, http_status, reason, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now(timezone.utc).isoformat(timespec='seconds'), ip,
             path[:4096], score, ml_label, action, status, reason, duration_ms))
        event_id=cursor.lastrowid
        if context is not None:
            con.execute('INSERT INTO download_context VALUES(?,?,?,?)',
                        (event_id,context['path_outcome'],context['visibility'],context['access_outcome']))
        if timing is not None:
            con.execute('INSERT INTO processing_timings VALUES(?,?,?,?)',
                        (event_id,timing['ids_ms'],timing['ips_ms'],timing['total_ms']))
        # Same transaction: an alert is durable before any Gemini work is queued.
        record_alert(con,event_id,ip,path,action,ml_label,
                     path_blocked=None if context is None else context['path_outcome']=='rejected')
        return event_id


def download_statistics(db_path, **filters):
    where,params=where_clause(**filters)
    with closing(connect(db_path)) as db:
        row=db.execute('''SELECT
            COALESCE(SUM(CASE WHEN action='BLOCK' AND COALESCE(c.access_outcome,'')!='login_required' THEN 1 ELSE 0 END),0) AS path_blocks,
            COALESCE(SUM(CASE WHEN c.access_outcome='login_required' THEN 1 ELSE 0 END),0) AS login_required
            FROM access_logs l LEFT JOIN download_context c ON c.event_id=l.id'''+where,params).fetchone()
        return dict(row)


def ips_statistics(db_path):
    """Return only persisted IPS observations; never synthesize dashboard data."""
    with closing(connect(db_path)) as db:
        totals = dict(db.execute('''SELECT COUNT(*) AS total,
            COALESCE(SUM(action='ALLOW'),0) AS allowed,
            COALESCE(SUM(action='MISS'),0) AS missing,
            COALESCE(SUM(action='BLOCK' AND COALESCE(c.access_outcome,'')!='login_required'),0) AS blocked,
            COALESCE(SUM(c.access_outcome='login_required'),0) AS login_required,
            COALESCE(SUM(ml_label='suspicious'),0) AS ids_suspicious
            FROM access_logs l LEFT JOIN download_context c ON c.event_id=l.id''').fetchone())
        reasons = [dict(row) for row in db.execute('''SELECT reason,COUNT(*) AS count
            FROM access_logs l LEFT JOIN download_context c ON c.event_id=l.id
            WHERE action='BLOCK' AND COALESCE(c.access_outcome,'')!='login_required'
            GROUP BY reason ORDER BY count DESC,reason LIMIT 20''')]
        timings = dict(db.execute('''SELECT COUNT(*) AS samples,
            COALESCE(AVG(ids_ms),0) AS ids_avg_ms,
            COALESCE(AVG(ips_ms),0) AS ips_avg_ms,
            COALESCE(AVG(total_ms),0) AS total_avg_ms,
            COALESCE(MAX(total_ms),0) AS total_max_ms FROM processing_timings''').fetchone())
        logs = [dict(row) for row in db.execute('''SELECT l.*,c.path_outcome,c.visibility,c.access_outcome,
            t.ids_ms,t.ips_ms,t.total_ms FROM access_logs l
            LEFT JOIN download_context c ON c.event_id=l.id
            LEFT JOIN processing_timings t ON t.event_id=l.id
            WHERE l.action='BLOCK' AND COALESCE(c.access_outcome,'')!='login_required'
            ORDER BY l.id DESC LIMIT 100''')]
        trend = [dict(row) for row in db.execute('''SELECT substr(created_at,1,16) AS minute,
            COUNT(*) AS total,
            SUM(action='BLOCK' AND COALESCE(c.access_outcome,'')!='login_required') AS blocked
            FROM access_logs l LEFT JOIN download_context c ON c.event_id=l.id
            GROUP BY minute ORDER BY minute DESC LIMIT 60''')]
    trend.reverse()
    return {'totals': totals, 'reasons': reasons, 'timings': timings, 'logs': logs, 'trend': trend}


def recent_logs(db_path, limit=100, action=None, ml_label=None, http_status=None, start=None, end=None):
    where, params = where_clause(action=action, ml_label=ml_label, http_status=http_status, start=start, end=end)
    with closing(connect(db_path)) as con, con:
        query = 'SELECT * FROM access_logs' + where + ' ORDER BY id DESC LIMIT ?'
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


def summary(db_path, **filters):
    where, params = where_clause(**filters)
    with closing(connect(db_path)) as con, con:
        result = dict(con.execute('''SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN action='BLOCK' THEN 1 ELSE 0 END) AS blocked,
            SUM(CASE WHEN action='ALLOW' THEN 1 ELSE 0 END) AS allowed,
            SUM(CASE WHEN ml_label='suspicious' THEN 1 ELSE 0 END) AS suspicious
            FROM access_logs''' + where, params).fetchone())
        return {key: value or 0 for key, value in result.items()}

def failed_password_change_count(db_path, ip, since):
    with closing(connect(db_path)) as con:
        return con.execute("SELECT COUNT(*) FROM security_events WHERE client_ip=? AND event='password_change_failed' AND created_at>=?",(ip,since)).fetchone()[0]
