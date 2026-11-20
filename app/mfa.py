"""Mandatory Admin TOTP and revocable server-side authentication references."""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
import time

from flask import session
import pyotp

from .account_store import audit, take_rate
from .database import connect
from .mfa_keys import KeyRing

DDL = '''
CREATE TABLE IF NOT EXISTS auth_mfa(
 subject TEXT PRIMARY KEY,seed_cipher TEXT NOT NULL,version TEXT NOT NULL,
 last_counter INTEGER NOT NULL DEFAULT -1,enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN(0,1)));
CREATE TABLE IF NOT EXISTS auth_mfa_challenges(
 digest TEXT PRIMARY KEY,subject TEXT NOT NULL,role TEXT NOT NULL,
 credential_version TEXT NOT NULL,mfa_version TEXT,expires REAL NOT NULL,
 used INTEGER NOT NULL DEFAULT 0 CHECK(used IN(0,1)),
 purpose TEXT NOT NULL,seed_cipher TEXT);
CREATE INDEX IF NOT EXISTS auth_mfa_challenge_subject ON auth_mfa_challenges(subject);
CREATE TABLE IF NOT EXISTS auth_backup_codes(
 digest TEXT PRIMARY KEY,subject TEXT NOT NULL,used INTEGER NOT NULL DEFAULT 0 CHECK(used IN(0,1)));
CREATE INDEX IF NOT EXISTS auth_backup_subject ON auth_backup_codes(subject);
CREATE TABLE IF NOT EXISTS auth_sessions(
 digest TEXT PRIMARY KEY,subject TEXT NOT NULL,credential_version TEXT NOT NULL,
 mfa_version TEXT,created REAL NOT NULL,last_seen REAL NOT NULL,absolute_expires REAL NOT NULL,
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN(0,1)));
CREATE INDEX IF NOT EXISTS auth_session_subject ON auth_sessions(subject);
'''


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    version: str
    user_id: int | None = None


class MFARejected(ValueError):
    pass


class MFARateLimited(MFARejected):
    pass


class MFAService:
    def __init__(self, app):
        self.app = app
        self.path = app.config['DATABASE']
        self.clock = time.time
        with closing(connect(self.path)) as db:
            states = db.execute('SELECT subject,seed_cipher FROM auth_mfa WHERE enabled=1').fetchall()
        self.keys = KeyRing(app.config['MFA_KEY_FILE'], app.config.get('MFA_KEYS'), bool(states))
        for state in states:
            self.keys.decrypt(state['subject'], state['seed_cipher'])

    def principal(self, role=None, user=None):
        if user is not None:
            return Principal('user:' + str(user['id']), user['role'], user['session_version'], user['id'])
        if role not in {'admin', 'auditor'}:
            raise MFARejected('Invalid principal')
        return Principal('legacy:' + role, role, self.app.extensions['credentials'].version(role))

    def current(self, subject, db):
        if subject in {'legacy:admin', 'legacy:auditor'}:
            return self.principal(role=subject.split(':')[1])
        if not re.fullmatch(r'user:[1-9][0-9]{0,18}', subject):
            raise MFARejected('Invalid principal')
        value = int(subject.split(':')[1])
        if value > 9223372036854775807:
            raise MFARejected('Invalid principal')
        row = db.execute('SELECT * FROM auth_users WHERE id=? AND active=1', (value,)).fetchone()
        if not row:
            raise MFARejected('Inactive principal')
        return self.principal(user=row)

    def create_challenge(self, principal, purpose='login', expected_mfa=None):
        if principal.role != 'admin' or purpose not in {'login', 'rotate'}:
            raise MFARejected('Admin MFA required')
        now = self.clock()
        if not take_rate(self.path, 'mfa_challenge', principal.subject, 10, 300):
            raise MFARateLimited('Too many first-factor challenges')
        token = secrets.token_urlsafe(32)
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if self.current(principal.subject, db) != principal:
                raise MFARejected('Credentials changed')
            state = db.execute('SELECT * FROM auth_mfa WHERE subject=? AND enabled=1', (principal.subject,)).fetchone()
            if purpose == 'rotate' and (not state or state['version'] != expected_mfa):
                raise MFARejected('Factor changed during reauthentication')
            seed = self.keys.encrypt(principal.subject, pyotp.random_base32()) if not state or purpose == 'rotate' else None
            mode = 'rotate' if purpose == 'rotate' else ('login' if state else 'enroll')
            db.execute('INSERT INTO auth_mfa_challenges VALUES(?,?,?,?,?,?,0,?,?)',
                       (digest(token), principal.subject, 'admin', principal.version,
                        state['version'] if state else None, now + 300, mode, seed))
        session.clear()
        session['_mfa_pending'] = token  # Opaque first-factor reference, no role or seed.
        return mode

    def pending(self, token, db):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            raise MFARejected('Challenge unavailable')
        row = db.execute('SELECT * FROM auth_mfa_challenges WHERE digest=? AND used=0 AND expires>?',
                         (digest(token), self.clock())).fetchone()
        if not row:
            raise MFARejected('Challenge unavailable')
        principal = self.current(row['subject'], db)
        if principal.role != 'admin' or not hmac.compare_digest(principal.version, row['credential_version']):
            raise MFARejected('Credentials changed')
        state = db.execute('SELECT * FROM auth_mfa WHERE subject=? AND enabled=1', (principal.subject,)).fetchone()
        expected = state['version'] if state else None
        if row['mfa_version'] != expected:
            raise MFARejected('Factor changed')
        return row, principal

    def enrollment(self):
        with closing(connect(self.path)) as db:
            row, principal = self.pending(session.get('_mfa_pending'), db)
        secret = self.keys.decrypt(principal.subject, row['seed_cipher']) if row['seed_cipher'] else None
        return row['purpose'], principal, secret

    def throttle(self, subject, ip):
        if (not take_rate(self.path, 'mfa_subject', subject, 5, 300)
                or not take_rate(self.path, 'mfa_ip', ip, 20, 300)):
            with closing(connect(self.path)) as db, db:
                audit(db, ip, 'anonymous', 'mfa_throttled')
            raise MFARateLimited('MFA rate limited')

    def consume_factor(self, db, subject, code):
        state = db.execute('SELECT * FROM auth_mfa WHERE subject=? AND enabled=1', (subject,)).fetchone()
        if not state:
            return False
        if re.fullmatch(r'[0-9]{6}', code):
            now = self.clock()
            counter = int(now // 30)
            secret = self.keys.decrypt(subject, state['seed_cipher'])
            if counter <= state['last_counter'] or not pyotp.TOTP(secret, interval=30).verify(code, for_time=now, valid_window=0):
                return False
            return bool(db.execute('UPDATE auth_mfa SET last_counter=? WHERE subject=? AND last_counter<? AND version=?',
                                   (counter, subject, counter, state['version'])).rowcount)
        normalized = code.replace('-', '').lower()
        if not re.fullmatch(r'[0-9a-f]{32}', normalized):
            return False
        # Recovery secrets have 128 random bits: SHA-256 is permitted by ASVS 6.5.2.
        return bool(db.execute('UPDATE auth_backup_codes SET used=1 WHERE digest=? AND subject=? AND used=0',
                               (digest(subject + ':' + normalized), subject)).rowcount)

    def issue(self, db, principal, mfa_version=None):
        if principal.role == 'admin' and not mfa_version:
            raise MFARejected('Admin second factor is mandatory')
        token = secrets.token_urlsafe(32)
        now = self.clock()
        active = db.execute('SELECT digest FROM auth_sessions WHERE subject=? AND revoked=0 ORDER BY created DESC',
                            (principal.subject,)).fetchall()
        for row in active[4:]:  # Keep at most five simultaneous sessions.
            db.execute('UPDATE auth_sessions SET revoked=1 WHERE digest=?', (row['digest'],))
        db.execute('INSERT INTO auth_sessions VALUES(?,?,?,?,?,?,?,0)',
                   (digest(token), principal.subject, principal.version, mfa_version, now, now, now + 8 * 3600))
        return token

    def cookie(self, principal, token):
        session.clear()
        session.permanent = True
        session.update(role=principal.role, is_admin=principal.role == 'admin',
                       _credential_version=principal.version, _auth_sid=token)
        if principal.user_id is not None:
            session['user_id'] = principal.user_id

    def grant_password_session(self, principal, ip):
        if principal.role == 'admin':
            raise MFARejected('Admin second factor is mandatory')
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if self.current(principal.subject, db) != principal:
                raise MFARejected('Credentials changed')
            token = self.issue(db, principal)
            audit(db, ip, principal.role, 'login_success')
            if principal.user_id is not None:
                audit(db, ip, principal.role, 'account_login_success:' + str(principal.user_id))
        self.cookie(principal, token)

    def confirm(self, code, ip):
        with closing(connect(self.path)) as db:
            row, principal = self.pending(session.get('_mfa_pending'), db)
        self.throttle(principal.subject, ip)
        backup = []
        success = False
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row, principal = self.pending(session.get('_mfa_pending'), db)
            if row['seed_cipher']:
                now = self.clock()
                secret = self.keys.decrypt(principal.subject, row['seed_cipher'])
                success = bool(re.fullmatch(r'[0-9]{6}', code) and pyotp.TOTP(secret).verify(code, for_time=now, valid_window=0))
                if success:
                    version = secrets.token_urlsafe(32)
                    db.execute('INSERT INTO auth_mfa VALUES(?,?,?,?,1) ON CONFLICT(subject) DO UPDATE SET seed_cipher=excluded.seed_cipher,version=excluded.version,last_counter=excluded.last_counter,enabled=1',
                               (principal.subject, row['seed_cipher'], version, int(now // 30)))
                    db.execute('UPDATE auth_backup_codes SET used=1 WHERE subject=?', (principal.subject,))
                    for _ in range(8):
                        raw = secrets.token_hex(16)
                        backup.append('-'.join(raw[i:i+8] for i in range(0, 32, 8)))
                        db.execute('INSERT INTO auth_backup_codes VALUES(?,?,0)', (digest(principal.subject + ':' + raw), principal.subject))
                    db.execute('UPDATE auth_sessions SET revoked=1 WHERE subject=?', (principal.subject,))
                    audit(db, ip, 'admin', 'mfa_' + row['purpose'] + ':' + principal.subject)
            else:
                success = self.consume_factor(db, principal.subject, code)
                if success:
                    version = row['mfa_version']
            if success:
                db.execute('DELETE FROM auth_rate_limits WHERE bucket=?',
                           ('mfa_subject:' + hashlib.sha256(principal.subject.encode()).hexdigest(),))
                db.execute('UPDATE auth_mfa_challenges SET used=1 WHERE digest=?', (row['digest'],))
                token = self.issue(db, principal, version)
                audit(db, ip, 'admin', 'login_success')
                audit(db, ip, 'admin', 'mfa_login_success:' + principal.subject)
                if principal.user_id is not None:
                    audit(db, ip, 'admin', 'account_login_success:' + str(principal.user_id))
            else:
                audit(db, ip, 'anonymous', 'mfa_failed')
        if not success:
            raise MFARejected('Invalid or reused factor')
        self.cookie(principal, token)
        return backup

    def validate_session(self, principal):
        value = session.get('_auth_sid')
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            return False
        now = self.clock()
        with closing(connect(self.path)) as db, db:
            row = db.execute('SELECT * FROM auth_sessions WHERE digest=? AND subject=? AND credential_version=? AND revoked=0 AND absolute_expires>? AND last_seen>?',
                             (digest(value), principal.subject, principal.version, now, now - 900)).fetchone()
            if not row:
                return False
            if principal.role == 'admin':
                state = db.execute('SELECT version FROM auth_mfa WHERE subject=? AND enabled=1', (principal.subject,)).fetchone()
                if not state or row['mfa_version'] != state['version']:
                    return False
            if now - row['last_seen'] >= 30:
                db.execute('UPDATE auth_sessions SET last_seen=? WHERE digest=? AND revoked=0', (now, digest(value)))
        return True

    def revoke_current(self):
        value = session.get('_auth_sid')
        if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            with closing(connect(self.path)) as db, db:
                db.execute('UPDATE auth_sessions SET revoked=1 WHERE digest=?', (digest(value),))

    def authorize_rotation(self, principal, code, ip):
        self.throttle(principal.subject, ip)
        with closing(connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            state = db.execute('SELECT version FROM auth_mfa WHERE subject=? AND enabled=1', (principal.subject,)).fetchone()
            if self.current(principal.subject, db) != principal or not self.consume_factor(db, principal.subject, code):
                raise MFARejected('Factor verification failed')
            audit(db, ip, 'admin', 'mfa_rotation_authorized:' + principal.subject)
        return self.create_challenge(principal, purpose='rotate', expected_mfa=state['version'])
