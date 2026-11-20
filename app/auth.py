"""Local-demo authentication, role checks and CSRF; no plaintext persistence."""
from datetime import timedelta
from functools import wraps
import hmac
from pathlib import Path
import secrets
import sqlite3

from flask import abort, redirect, request, session, url_for,g
from flask.sessions import SecureCookieSessionInterface
from .passwords import password_hash

from .database import insert_security_event


def configure_auth(app, base):
    class TransportSessionInterface(SecureCookieSessionInterface):
        def get_cookie_secure(self,application):
            return bool(application.config['SESSION_COOKIE_SECURE'] or request.is_secure)
    app.session_interface=TransportSessionInterface()
    app.config.setdefault('CSRF_ENABLED', not app.testing)
    app.config.setdefault('LOGIN_MAX_FAILURES', 5)
    app.config.setdefault('LOGIN_WINDOW_SECONDS', 300)
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(minutes=15))
    from .credential_store import Credentials, credential_lock, atomic_hash_write, read_hash, validate_hash
    path = Path(app.config['ADMIN_HASH_FILE'])
    with credential_lock(path):
        if not path.exists():
            stored = app.config.get('ADMIN_PASSWORD_HASH')
            password = app.config.get('ADMIN_PASSWORD')
            if not stored and not password:
                raise ValueError('Configure admin first: python tools/manage_credentials.py')
            if not stored and not 6 <= len(password) <= 128:
                raise ValueError('Bootstrap password must contain 6-128 characters')
            atomic_hash_write(path, stored or password_hash(password))
        stored = read_hash(path)  # Existing valid file always wins; no silent reset.
    app.config['ADMIN_HASH'] = stored
    auditor_file = Path(app.config['AUDITOR_HASH_FILE'])
    app.config['AUDITOR_HASH'] = read_hash(auditor_file) if auditor_file.is_file() else app.config.get('AUDITOR_PASSWORD_HASH')
    if app.config['AUDITOR_HASH']:
        validate_hash(app.config['AUDITOR_HASH'])
    app.config['BOOTSTRAP_PASSWORD'] = None
    app.config.pop('ADMIN_PASSWORD', None)
    app.extensions['credentials'] = Credentials(app)
    app.config.setdefault('PASSWORD_CHANGE_MAX_FAILURES', 5)
    app.config.setdefault('PASSWORD_CHANGE_WINDOW_SECONDS', 300)

    @app.before_request
    def check_session_version():
        g.account=None
        role = session.get('role')
        if 'user_id' in session:
            from .account_store import find
            user_id=session.get('user_id')
            try:
                row=find(app.config['DATABASE'],user_id=user_id) if type(user_id) is int and 0<user_id<=9223372036854775807 else None
                supplied=session.get('_credential_version','')
                valid=bool(row and row['active'] and row['role']==role and isinstance(supplied,str) and supplied.isascii() and hmac.compare_digest(supplied,row['session_version']))
                if valid:
                    valid=app.extensions['mfa'].validate_session(app.extensions['mfa'].principal(user=row))
            except sqlite3.Error:
                session.clear();abort(503)
            if not valid:session.clear()
            else:g.account=row
            return
        if role:
            if role not in {'admin','auditor'}:
                session.clear();return
            try:
                expected = app.extensions['credentials'].version(role)
            except (OSError, ValueError):
                session.clear()
                abort(503)
            supplied = session.get('_credential_version', '')
            try:
                valid = isinstance(supplied, str) and hmac.compare_digest(supplied, expected)
            except TypeError:
                valid = False
            if not valid:
                session.clear()
            elif not app.extensions['mfa'].validate_session(app.extensions['mfa'].principal(role=role)):
                session.clear()

    @app.before_request
    def require_secure_account_transport():
        sensitive=request.endpoint in {'login','change_password','logout'} or (request.endpoint or '').startswith(('accounts.','mfa.'))
        if not app.testing and sensitive and not request.is_secure:
            local=request.remote_addr in {'127.0.0.1','::1'} and request.host.split(':')[0] in {'localhost','127.0.0.1','[::1]'}
            if not local:abort(400,description='HTTPS is required for account access')

    def csrf_token():
        if '_csrf' not in session:
            session['_csrf'] = secrets.token_urlsafe(32)
        return session['_csrf']

    app.context_processor(lambda: {'csrf_token': csrf_token})

    @app.before_request
    def check_csrf():
        if request.method != 'POST' or not app.config['CSRF_ENABLED']:
            return None
        submitted = request.form.get('csrf_token', request.headers.get('X-CSRF-Token', ''))
        expected = session.get('_csrf', '')
        try:
            valid = bool(expected) and len(submitted) <= 256 and hmac.compare_digest(expected, submitted)
        except TypeError:
            valid = False
        if not valid:
            try:
                insert_security_event(app.config['DATABASE'], request.remote_addr or 'unknown',
                                      session.get('role', 'anonymous'), 'csrf_rejected')
            except sqlite3.Error:
                app.logger.exception('CSRF rejection audit unavailable')
            abort(403)


def roles_required(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get('role')
            if role is None:
                return redirect(url_for('login'))
            if role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate
