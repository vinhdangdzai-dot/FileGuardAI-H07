"""Account persistence, additive migration and Werkzeug password verification."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import re
import secrets
import time
from .passwords import password_hash, check_password_hash, needs_upgrade
from .database import connect

clock=time.time
DUMMY_HASH=password_hash(secrets.token_urlsafe(24))  # Not an account or shared default password.

MIGRATION='''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS auth_schema_versions(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS auth_users(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 display_name TEXT NOT NULL,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin','auditor','user')),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 session_version TEXT NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS auth_reset_tokens(
 digest TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES auth_users(id),
 credential_version TEXT NOT NULL,expires REAL NOT NULL,used INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0,1)));
CREATE INDEX IF NOT EXISTS auth_reset_user ON auth_reset_tokens(user_id);
CREATE TABLE IF NOT EXISTS auth_rate_limits(
 bucket TEXT PRIMARY KEY,count INTEGER NOT NULL,until REAL NOT NULL);
INSERT OR IGNORE INTO auth_schema_versions VALUES(1,strftime('%Y-%m-%dT%H:%M:%SZ','now'));'''


def migrate(path):
    from .mfa import DDL as MFA_DDL
    with closing(connect(path)) as db:
        try:
            db.executescript(MIGRATION+MFA_DDL)
            if db.execute('SELECT MAX(version) FROM auth_schema_versions').fetchone()[0] not in {1,2}:raise RuntimeError('Unsupported account schema version')
            expected={'auth_users':{'id','username','email','display_name','password_hash','role','active','session_version','created_at','updated_at'},
                      'auth_reset_tokens':{'digest','user_id','credential_version','expires','used'},
                      'auth_rate_limits':{'bucket','count','until'}}
            for table,columns in expected.items():
                if not columns<={r[1] for r in db.execute('PRAGMA table_info('+table+')')}:raise RuntimeError('Unsupported account table structure')
            for table,columns in {'auth_mfa':{'subject','seed_cipher','version','last_counter','enabled'},
                                  'auth_mfa_challenges':{'digest','subject','role','credential_version','mfa_version','expires','used','purpose','seed_cipher'},
                                  'auth_backup_codes':{'digest','subject','used'},
                                  'auth_sessions':{'digest','subject','credential_version','mfa_version','created','last_seen','absolute_expires','revoked'}}.items():
                if not columns<={r[1] for r in db.execute('PRAGMA table_info('+table+')')}:raise RuntimeError('Unsupported MFA/session table structure')
            db.execute('INSERT OR IGNORE INTO auth_schema_versions VALUES(2,?)',(stamp(),))
            db.commit()
        except Exception:db.rollback();raise


def stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')


def audit(db,ip,role,event):
    db.execute('INSERT INTO security_events(created_at,client_ip,actor_role,event) VALUES(?,?,?,?)',(stamp(),ip,role,event))


def identity(value):return value.strip().casefold()


def validate_identity(username,email):
    username=identity(username);email=identity(email)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{2,31}',username) or username in {'admin','administrator','auditor'}:raise ValueError('username')
    if len(email)>254 or not re.fullmatch(r'[a-z0-9][a-z0-9._%+-]{0,63}@[a-z0-9.-]+',email):raise ValueError('email')
    domain=email.split('@')[1]
    if '.' not in domain or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')):raise ValueError('email')
    return username,email


def display(value):
    value=value.strip()
    if not 1<=len(value)<=100 or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('display_name')
    return value


def take_rate(path,scope,value,limit,seconds):
    # Hash identifiers for the rate bucket; this is NOT password hashing.
    bucket=scope+':'+hashlib.sha256(value.encode()).hexdigest();now=clock()
    with closing(connect(path)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT count,until FROM auth_rate_limits WHERE bucket=?',(bucket,)).fetchone()
        if row and row['until']>now and row['count']>=limit:return False
        if row and row['until']>now:db.execute('UPDATE auth_rate_limits SET count=count+1 WHERE bucket=?',(bucket,))
        else:db.execute('INSERT INTO auth_rate_limits VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=1,until=excluded.until',(bucket,now+seconds))
    return True


def find(path,identifier=None,user_id=None):
    with closing(connect(path)) as db:
        if user_id is not None:return db.execute('SELECT * FROM auth_users WHERE id=?',(user_id,)).fetchone()
        name=identity(identifier or '')
        return db.execute('SELECT * FROM auth_users WHERE username=? OR email=?',(name,name)).fetchone()


def clear_login_rate(path,identifier):
    bucket='login_identity:'+hashlib.sha256(identity(identifier).encode()).hexdigest()
    with closing(connect(path)) as db,db:db.execute('DELETE FROM auth_rate_limits WHERE bucket=?',(bucket,))


def revoke_user_sessions(db,user_id):
    subject='user:'+str(user_id)
    db.execute('UPDATE auth_sessions SET revoked=1 WHERE subject=?',(subject,))
    db.execute('UPDATE auth_mfa_challenges SET used=1 WHERE subject=?',(subject,))


def authenticate(path,identifier,password):
    row=find(path,identifier=identifier)
    valid=check_password_hash(row['password_hash'] if row else DUMMY_HASH,password if len(password)<=128 else '')
    if not (valid and row and row['active']):return None
    if needs_upgrade(row['password_hash']):
        upgraded=password_hash(password)
        with closing(connect(path)) as db,db:
            changed=db.execute('UPDATE auth_users SET password_hash=? WHERE id=? AND password_hash=? AND session_version=? AND active=1',
                               (upgraded,row['id'],row['password_hash'],row['session_version']))
            if not changed.rowcount:return None
        row=find(path,user_id=row['id'])
        if not row or not row['active'] or not check_password_hash(row['password_hash'],password):return None
    return row


def register(path,username,email,name,password,ip):
    username,email=validate_identity(username,email);name=display(name or username)
    hashed=password_hash(password);now=stamp()
    with closing(connect(path)) as db,db:
        cursor=db.execute('INSERT INTO auth_users(username,email,display_name,password_hash,session_version,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                   (username,email,name,hashed,secrets.token_urlsafe(32),now,now))
        audit(db,ip,'anonymous','account_registered:'+str(cursor.lastrowid))


def issue_reset(path,identifier,ip,ttl=900):
    token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
    with closing(connect(path)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        name=identity(identifier)
        row=db.execute('SELECT * FROM auth_users WHERE (username=? OR email=?) AND active=1',(name,name)).fetchone()
        audit(db,ip,'anonymous','password_reset_requested')
        if row:
            db.execute('UPDATE auth_reset_tokens SET used=1 WHERE user_id=?',(row['id'],))
            db.execute('INSERT INTO auth_reset_tokens VALUES(?,?,?,?,0)',(digest,row['id'],row['session_version'],clock()+ttl))
            return row['email'],token,digest
    return None


def reset_password(path,token,new_password,ip):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):return False
    digest=hashlib.sha256(token.encode()).hexdigest();hashed=password_hash(new_password)
    with closing(connect(path)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('''SELECT t.user_id FROM auth_reset_tokens t JOIN auth_users u ON u.id=t.user_id
                         WHERE t.digest=? AND t.used=0 AND t.expires>? AND u.active=1 AND t.credential_version=u.session_version''',(digest,clock())).fetchone()
        if not row:return False
        db.execute('UPDATE auth_users SET password_hash=?,session_version=?,updated_at=? WHERE id=?',(hashed,secrets.token_urlsafe(32),stamp(),row['user_id']))
        db.execute('UPDATE auth_reset_tokens SET used=1 WHERE user_id=?',(row['user_id'],))
        revoke_user_sessions(db,row['user_id'])
        audit(db,ip,'anonymous','password_reset_success:'+str(row['user_id']))
    return True
