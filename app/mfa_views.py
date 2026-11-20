"""Admin MFA enrollment, second-factor challenge and authenticated rotation."""
from contextlib import closing
import io
import re

from flask import Blueprint, abort, current_app, g, redirect, render_template, request, send_file, session, url_for
import pyotp
import qrcode
import qrcode.image.svg

from .auth import roles_required
from .database import connect, insert_security_event
from .mfa import MFARejected, MFARateLimited, digest
from .passwords import check_password_hash
from .account_store import take_rate

bp = Blueprint('mfa', __name__)


def service():
    return current_app.extensions['mfa']


def ip():
    return request.remote_addr or 'unknown'


@bp.route('/login/mfa', methods=['GET', 'POST'])
def verify():
    if session.get('role') and not session.get('_mfa_pending'):
        return redirect(url_for('mfa.settings' if session['role']=='admin' else 'accounts.profile'))
    try:
        mode, principal, secret = service().enrollment()
    except MFARejected:
        session.clear()
        return redirect(url_for('login'))
    error = None
    status = 200
    if request.method == 'POST':
        try:
            codes = service().confirm(request.form.get('code', '').strip(), ip())
            if codes:
                return render_template('mfa_codes.html', codes=codes)
            return redirect(url_for('dashboard'))
        except MFARateLimited:
            error = 'Thử mã quá nhiều lần. Vui lòng chờ 5 phút và đăng nhập lại.'
            status = 429
        except MFARejected:
            error = 'Mã không hợp lệ, đã sử dụng hoặc bước xác thực đã hết hạn.'
            status = 403
    return render_template('mfa_verify.html', mode=mode, secret=secret, error=error), status


@bp.get('/login/mfa/qr')
def qr():
    if not session.get('_mfa_pending') or session.get('role'):
        abort(404)
    _, principal, secret = service().enrollment()
    if not secret:
        abort(404)
    uri = pyotp.TOTP(secret).provisioning_uri(name=principal.subject, issuer_name='CANH GÁC SỐ')
    result = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(result)
    result.seek(0)
    return send_file(result, mimetype='image/svg+xml', download_name='mfa-setup.svg', max_age=0)


@bp.post('/login/mfa/cancel')
def cancel():
    if session.get('role') and not session.get('_mfa_pending'):
        return redirect(url_for('accounts.profile'))
    value = session.get('_mfa_pending')
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        with closing(connect(current_app.config['DATABASE'])) as db, db:
            db.execute('UPDATE auth_mfa_challenges SET used=1 WHERE digest=?', (digest(value),))
    session.clear()
    return redirect(url_for('login'))


@bp.route('/account/mfa', methods=['GET', 'POST'])
@roles_required('admin')
def settings():
    account = getattr(g, 'account', None)
    principal = service().principal(user=account) if account is not None else service().principal(role='admin')
    error = None
    status = 200
    if request.method == 'POST':
        if not take_rate(current_app.config['DATABASE'], 'mfa_settings', principal.subject, 5, 300):
            raise MFARateLimited()
        stored = account['password_hash'] if account is not None else current_app.extensions['credentials'].current('admin')
        if not check_password_hash(stored, request.form.get('current_password', '')):
            insert_security_event(current_app.config['DATABASE'], ip(), 'admin', 'mfa_settings_reauth_failed')
            error = 'Không xác minh được yêu cầu đổi thiết bị xác thực.'
            status = 403
        else:
            try:
                service().authorize_rotation(principal, request.form.get('code', '').strip(), ip())
                return redirect(url_for('mfa.verify'))
            except MFARateLimited:
                raise
            except MFARejected:
                error = 'Không xác minh được yêu cầu đổi thiết bị xác thực.'
                status = 403
    with closing(connect(current_app.config['DATABASE'])) as db:
        remaining = db.execute('SELECT COUNT(*) FROM auth_backup_codes WHERE subject=? AND used=0', (principal.subject,)).fetchone()[0]
    return render_template('mfa_settings.html', remaining=remaining, error=error), status
