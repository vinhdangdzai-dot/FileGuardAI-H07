"""Local-demo authentication, role checks and CSRF; no plaintext persistence."""
from datetime import timedelta
from functools import wraps
import hmac
from pathlib import Path
import secrets
import sqlite3

from flask import abort, redirect, request, session, url_for
from werkzeug.security import generate_password_hash

from .database import insert_security_event


def configure_auth(app, base):
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
            atomic_hash_write(path, stored or generate_password_hash(password))
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
        role = session.get('role')
        if role:
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
