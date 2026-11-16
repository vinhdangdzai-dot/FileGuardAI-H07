"""Local-demo authentication, role checks and CSRF; no plaintext persistence."""
from datetime import timedelta
from functools import wraps
import hmac
from pathlib import Path
import secrets

from flask import abort, redirect, request, session, url_for
from werkzeug.security import generate_password_hash

from .database import insert_security_event


def configure_auth(app, base):
    app.config.setdefault('CSRF_ENABLED', not app.testing)
    app.config.setdefault('LOGIN_MAX_FAILURES', 5)
    app.config.setdefault('LOGIN_WINDOW_SECONDS', 300)
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(minutes=15))
    stored = app.config.get('ADMIN_PASSWORD_HASH')
    path = Path(app.config.get('ADMIN_HASH_FILE', base / 'instance/admin_password.hash'))
    if not stored and path.is_file() and not app.testing:
        stored = path.read_text(encoding='utf-8').strip()
    if stored and not stored.startswith(('scrypt:', 'pbkdf2:')):
        raise ValueError('ADMIN_PASSWORD_HASH must be a Werkzeug password hash')
    app.config['ADMIN_HASH'] = stored or generate_password_hash(app.config['ADMIN_PASSWORD'])
    auditor = app.config.get('AUDITOR_PASSWORD_HASH')
    auditor_file = Path(app.config.get('AUDITOR_HASH_FILE', base / 'instance/auditor_password.hash'))
    if not auditor and auditor_file.is_file() and not app.testing:
        auditor = auditor_file.read_text(encoding='utf-8').strip()
    if auditor and not auditor.startswith(('scrypt:', 'pbkdf2:')):
        raise ValueError('AUDITOR_PASSWORD_HASH must be a Werkzeug password hash')
    app.config['AUDITOR_HASH'] = auditor
    app.config['BOOTSTRAP_PASSWORD'] = None if stored else app.config['ADMIN_PASSWORD']

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
            insert_security_event(app.config['DATABASE'], request.remote_addr or 'unknown',
                                  session.get('role', 'anonymous'), 'csrf_rejected')
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
