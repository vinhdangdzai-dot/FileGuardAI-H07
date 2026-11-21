"""Immediate, local advisory alerts. No provider calls or authorization changes."""
import hashlib
import json
from time import time as clock
from .ai_explanations import safe_features

DDL = '''
CREATE TABLE IF NOT EXISTS alerts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 first_event_id INTEGER NOT NULL REFERENCES access_logs(id),
 last_event_id INTEGER NOT NULL REFERENCES access_logs(id),
 rule TEXT NOT NULL, priority TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'new' CHECK(state IN ('new','seen','resolved')),
 occurrences INTEGER NOT NULL DEFAULT 1,
 created REAL NOT NULL, updated REAL NOT NULL, fingerprint TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS alerts_dedup ON alerts(fingerprint,created);
CREATE TABLE IF NOT EXISTS alert_events (
 event_id INTEGER PRIMARY KEY REFERENCES access_logs(id),
 alert_id INTEGER NOT NULL REFERENCES alerts(id));
CREATE INDEX IF NOT EXISTS alert_events_alert ON alert_events(alert_id);
CREATE TABLE IF NOT EXISTS alert_settings (
 id INTEGER PRIMARY KEY CHECK(id=1), notifications INTEGER NOT NULL CHECK(notifications IN (0,1)));
'''

RULES={'policy_block':'Chính sách từ chối truy cập (không xác nhận khai thác thành công)',
       'ml_suspicious':'Logistic Regression cảnh báo nghi vấn (có thể dự đoán sai)'}


def record(con,event_id,ip,path,action,label,now=None,*,path_blocked=None):
    blocked=action=='BLOCK' if path_blocked is None else path_blocked
    rule='policy_block' if blocked else 'ml_suspicious' if label=='suspicious' else None
    if rule is None:return
    priority='high' if rule=='policy_block' else 'medium'
    now=clock() if now is None else now
    feature_action='ALLOW' if action=='BLOCK' and not blocked else action
    fingerprint=hashlib.sha256(json.dumps([ip,rule,safe_features(path,feature_action,label=='suspicious')],sort_keys=True).encode()).hexdigest()
    # Fixed 60s window, same source/rule/coarse structure. Every event is retained.
    existing=con.execute("SELECT id FROM alerts WHERE fingerprint=? AND created>? AND state!='resolved' ORDER BY id DESC LIMIT 1",(fingerprint,now-60)).fetchone()
    if existing:
        alert_id=existing[0]
        con.execute('UPDATE alerts SET last_event_id=?,updated=?,occurrences=occurrences+1 WHERE id=?',(event_id,now,alert_id))
    else:
        alert_id=con.execute('INSERT INTO alerts(first_event_id,last_event_id,rule,priority,created,updated,fingerprint) VALUES(?,?,?,?,?,?,?)',
                             (event_id,event_id,rule,priority,now,now,fingerprint)).lastrowid
    con.execute('INSERT INTO alert_events VALUES(?,?)',(event_id,alert_id))


def settings(con):
    row=con.execute('SELECT notifications FROM alert_settings WHERE id=1').fetchone()
    return bool(row[0]) if row else True


def listing(con,state='',priority='',page=1):
    if state not in {'','new','seen','resolved'} or priority not in {'','high','medium'}:raise ValueError('Invalid alert filter')
    if not 1<=page<=2147483647:raise ValueError('Invalid page')
    clauses=[];params=[]
    for key,value in [('state',state),('priority',priority)]:
        if value:clauses.append(key+'=?');params.append(value)
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    total=con.execute('SELECT COUNT(*) FROM alerts'+where,params).fetchone()[0]
    rows=[dict(r) for r in con.execute('SELECT * FROM alerts'+where+' ORDER BY id DESC LIMIT 50 OFFSET ?',params+[(page-1)*50])]
    return rows,total
