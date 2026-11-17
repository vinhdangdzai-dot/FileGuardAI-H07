"""H07 Path Traversal Lab – Flask application factory."""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import time
import csv
import io
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import check_password_hash

from .database import (init_db, insert_log, recent_logs, summary, insert_security_event,
                       recent_security_events, failed_login_count)
from .auth import configure_auth, roles_required
from .log_filters import normalize_filters
from .evaluation_results import validate_evaluation
from .ml_features import extract_features
from .training_view import read_dataset, dataset_stats, dataset_page, inspect_models, evaluation_history
from .security import RejectedPath, list_allowed_files, open_authorized

BASE = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
        FILES_ROOT=BASE / 'shared_files',
        DATABASE=BASE / 'instance' / 'events.sqlite3',
        MODEL_PATH=BASE / 'artifacts' / 'model.joblib',
        EVALUATION_ROOT=BASE / 'docs' / 'evaluations',
        TRAINING_DATA_PATH=BASE / 'data/paths_synthetic.csv',
        EXPERIMENTAL_MODEL_PATH=BASE / 'docs/evaluations/20261116T154448Z_7a27a7/improved_model.joblib',
        ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD'),
        ADMIN_PASSWORD_HASH=os.environ.get('ADMIN_PASSWORD_HASH'),
        AUDITOR_PASSWORD_HASH=os.environ.get('AUDITOR_PASSWORD_HASH'),
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    if config:
        app.config.update(config)
    if app.config.get('TESTING') and 'ADMIN_PASSWORD' not in (config or {}):
        app.config['ADMIN_PASSWORD'] = 'test-only-secret'
    private_base = Path(app.config['DATABASE']).parent if app.testing else BASE / 'instance'
    app.config.setdefault('ADMIN_HASH_FILE', private_base / 'admin_password.hash')
    app.config.setdefault('AUDITOR_HASH_FILE', private_base / 'auditor_password.hash')

    root = Path(app.config['FILES_ROOT'])
    for private in (app.config['DATABASE'], app.config['MODEL_PATH'], app.config['TRAINING_DATA_PATH'],
                    app.config['EXPERIMENTAL_MODEL_PATH'], app.config['EVALUATION_ROOT'],
                    app.config.get('ADMIN_HASH_FILE', BASE / 'instance/admin_password.hash'),
                    app.config.get('AUDITOR_HASH_FILE', BASE / 'instance/auditor_password.hash')):
        if Path(private).resolve().is_relative_to(root.resolve()):
            raise ValueError('Private logs, credentials and model must be outside FILES_ROOT')
    configure_auth(app, BASE)
    root.mkdir(parents=True, exist_ok=True)
    init_db(Path(app.config['DATABASE']))

    predictor = None
    model_status = 'unavailable'
    model_path = Path(app.config['MODEL_PATH'])
    if model_path.exists():
        import joblib
        # Only load locally produced artifacts; joblib is pickle-based.
        try:
            predictor = joblib.load(model_path)
            if not callable(getattr(predictor, 'predict_proba', None)):
                raise ValueError('Artifact does not implement predict_proba')
            model_status = 'ready'
        except Exception:
            # AI is advisory: a broken local artifact must not disable the
            # independent file boundary. Never load untrusted pickle files.
            model_status = 'error'
            predictor = None
            app.logger.exception('Cannot load advisory ML artifact')

    def score_path(text):
        if len(text) > 4096:
            return None, 'skipped'
        if predictor is None:
            return None, ('error' if model_status == 'error' else 'unavailable')
        try:
            probability = float(predictor.predict_proba([extract_features(text)])[0][1])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError('Invalid probability')
            return probability, ('suspicious' if probability >= 0.5 else 'benign')
        except Exception:
            app.logger.exception('Advisory ML inference failed')
            return None, 'error'

    admin_required = roles_required('admin')

    @app.after_request
    def secure_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.error('SQLite operation unavailable', exc_info=True)
        return render_template('error.html', code=503, message='Kho nhật ký tạm thời không khả dụng.'), 503

    @app.get('/')
    def index():
        return render_template('index.html', files=list_allowed_files(root),
                               model_ready=predictor is not None)

    @app.get('/download')
    def download():
        start = time.perf_counter()
        # Flask decodes query transport once. Preserve this value for AI/logs;
        # security rejects residual structural escapes without decoding again.
        raw = request.args.get('path', '')
        score, ml_label = score_path(raw)
        ip = request.remote_addr or 'unknown'
        f = None
        try:
            if len(request.args.getlist('path')) != 1:
                raise RejectedPath('Yêu cầu phải có đúng một tham số path')
            f = open_authorized(root, raw)
            # We send an *already opened* file handle, never an unchecked path.
            response = send_file(f, as_attachment=True,
                                 download_name=raw.split('/')[-1],
                                 mimetype='application/octet-stream')
            response.call_on_close(f.close)
            action, status, reason = 'ALLOW', 200, 'Nằm trong thư mục cho phép'
        except (RejectedPath, PermissionError) as exc:
            if f is not None:
                f.close()
            action, status, reason = 'BLOCK', 403, str(exc) or 'Không được phép truy cập'
            response = render_template('error.html', code=403, message=reason), 403
        except (FileNotFoundError, NotADirectoryError):
            action, status, reason = 'MISS', 404, 'Không tìm thấy tệp'
            response = render_template('error.html', code=404, message=reason), 404
        except OSError:
            action, status, reason = 'BLOCK', 403, 'Yêu cầu không thể truy cập'
            response = render_template('error.html', code=403, message=reason), 403
        try:
            insert_log(app.config['DATABASE'], ip, raw, score, ml_label,
                       action, status, reason, (time.perf_counter() - start) * 1000)
        except (sqlite3.Error, ValueError):
            if f is not None:
                f.close()
            app.logger.exception('Cannot persist access event; file response withheld')
            return render_template('error.html', code=503, message='Không thể ghi nhật ký. Vui lòng thử lại sau.'), 503
        return response

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            ip = request.remote_addr or 'unknown'
            since = (datetime.now(timezone.utc) - timedelta(seconds=app.config['LOGIN_WINDOW_SECONDS'])).isoformat(timespec='seconds')
            if failed_login_count(app.config['DATABASE'], ip, since) >= app.config['LOGIN_MAX_FAILURES']:
                insert_security_event(app.config['DATABASE'], ip, 'anonymous', 'login_throttled')
                return 'Thử đăng nhập quá nhiều lần. Vui lòng thử lại sau.', 429, {'Retry-After': str(app.config['LOGIN_WINDOW_SECONDS'])}
            role = request.form.get('role', 'admin')
            try:
                password_hash = app.extensions['credentials'].current(role) if role in {'admin','auditor'} else None
            except (OSError, ValueError):
                return render_template('error.html',code=503,message='Kho thông tin xác thực tạm thời không khả dụng.'),503
            supplied_password = request.form.get('password', '')
            if len(supplied_password) <= 128 and password_hash and check_password_hash(password_hash, supplied_password):
                # Persist the authentication event BEFORE granting a role.
                insert_security_event(app.config['DATABASE'], ip, role, 'login_success')
                session.clear()
                session.permanent = True
                session['is_admin'] = role == 'admin'
                session['role'] = role
                session['_credential_version'] = app.extensions['credentials'].version(role, password_hash)
                return redirect(url_for('dashboard' if role == 'admin' else 'index'))
            insert_security_event(app.config['DATABASE'], ip, 'anonymous', 'login_failed')
            flash('Sai mật khẩu quản trị.')
        return render_template('login.html')

    @app.route('/account/password', methods=['GET', 'POST'])
    @admin_required
    def change_password():
        from .credential_store import credential_lock, atomic_hash_write
        from .database import failed_password_change_count
        from werkzeug.security import generate_password_hash
        error, status, committed = None, 200, False
        if request.method == 'POST':
            ip = request.remote_addr or 'unknown'
            window = app.config['PASSWORD_CHANGE_WINDOW_SECONDS']
            since = (datetime.now(timezone.utc)-timedelta(seconds=window)).isoformat(timespec='seconds')
            if failed_password_change_count(app.config['DATABASE'],ip,since) >= app.config['PASSWORD_CHANGE_MAX_FAILURES']:
                insert_security_event(app.config['DATABASE'],ip,'admin','password_change_throttled')
                return render_template('change_password.html',error='Thử quá nhiều lần. Vui lòng thử lại sau.'),429,{'Retry-After':str(window)}
            current = request.form.get('current_password','')
            new = request.form.get('new_password','')
            confirmation = request.form.get('confirm_password','')
            try:
                with credential_lock(app.config['ADMIN_HASH_FILE']):
                    # Recheck under the cross-process lock; no stale worker may
                    # overwrite a concurrent password change with old credentials.
                    if len(current)>128 or not check_password_hash(app.extensions['credentials'].current('admin'),current):
                        error,status = 'Mật khẩu hiện tại không đúng.',403
                    elif not 6 <= len(new) <= 128 or new != confirmation:
                        error,status = 'Mật khẩu mới cần 6–128 ký tự và xác nhận trùng khớp.',400
                    elif check_password_hash(app.extensions['credentials'].current('admin'),new):
                        error,status = 'Hãy chọn mật khẩu khác mật khẩu hiện tại.',400
                    if error:
                        insert_security_event(app.config['DATABASE'],ip,'admin','password_change_failed')
                    else:
                        # Fail before mutation if the audit store is unavailable.
                        insert_security_event(app.config['DATABASE'],ip,'admin','password_change_requested')
                        atomic_hash_write(app.config['ADMIN_HASH_FILE'],generate_password_hash(new))
                        committed = True
            except OSError:
                if not committed:
                    insert_security_event(app.config['DATABASE'],ip,'admin','password_change_write_failed')
                    return render_template('change_password.html',error='Không thể lưu thay đổi. Mật khẩu hiện có vẫn được giữ nguyên.'),503
                app.logger.error('Password changed; credential lock release unavailable')
            if not error:
                session.clear()
                try:
                    insert_security_event(app.config['DATABASE'],ip,'admin','password_change_success')
                except sqlite3.Error:
                    # File commit already happened: never report the old password
                    # as active or silently roll back the revocation.
                    app.logger.error('Password changed; success audit unavailable')
                flash('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.','success')
                return redirect(url_for('login'))
        return render_template('change_password.html',error=error),status

    @app.post('/logout')
    @roles_required('admin', 'auditor')
    def logout():
        try:
            insert_security_event(app.config['DATABASE'], request.remote_addr or 'unknown', session['role'], 'logout')
        except sqlite3.Error:
            app.logger.exception('Logout audit unavailable; session will still be cleared')
        finally:
            session.clear()
        return redirect(url_for('index'))

    @app.get('/dashboard')
    @admin_required
    def dashboard():
        try:
            filters = normalize_filters(**{key: request.args.get(key) for key in ('action', 'ml_label', 'http_status', 'start', 'end')})
        except ValueError:
            abort(400)
        logs = recent_logs(app.config['DATABASE'], **filters)
        counts = summary(app.config['DATABASE'], **filters)
        return render_template('dashboard.html', logs=logs, counts=counts,
                               security_events=recent_security_events(app.config['DATABASE']), filters=filters)

    @app.post('/dashboard/logs/export')
    @roles_required('admin')
    def export_logs():
        fields = ['id', 'created_at', 'client_ip', 'requested_path', 'ml_score', 'ml_label', 'action', 'http_status', 'reason', 'duration_ms']
        buffer = io.StringIO(newline='')
        writer = csv.writer(buffer)
        writer.writerow(fields)
        try:
            filters = normalize_filters(**{key: request.form.get(key) for key in ('action', 'ml_label', 'http_status', 'start', 'end')})
        except ValueError:
            abort(400)
        for row in recent_logs(app.config['DATABASE'], 500, **filters):
            writer.writerow([("'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value)
                             if isinstance(value := row[k], str) else value for k in fields])
        insert_security_event(app.config['DATABASE'], request.remote_addr or 'unknown', 'admin', 'logs_exported')
        return send_file(io.BytesIO(buffer.getvalue().encode('utf-8-sig')), as_attachment=True,
                         download_name='access_logs.csv', mimetype='text/csv')

    @app.get('/dashboard/ai-training')
    @admin_required
    def ai_training():
        page = None
        try:
            rows = read_dataset(app.config['TRAINING_DATA_PATH'])
            dataset = dataset_stats(rows, app.config['TRAINING_DATA_PATH'])
        except (OSError, ValueError, UnicodeError):
            dataset = None
        if dataset:
            try:
                page = dataset_page(rows, request.args)
            except ValueError:
                abort(400)
        history = evaluation_history(app.config['EVALUATION_ROOT'])
        # Prefer a validated strict run without changing the global latest pointer.
        selected = request.args.get('run')
        if selected is not None and selected not in {r['run'] for r in history}:
            abort(404)
        if selected is None:
            selected = next((r['run'] for r in history
                             if r.get('experiment_type') == 'canonical_grouped_validation'), None)
        evaluation, folder = evaluation_data(selected) if selected else (None, None)
        models = inspect_models(predictor, app.config['EXPERIMENTAL_MODEL_PATH'])
        return render_template('ai_training.html', dataset=dataset, models=models,
                               history=history, dataset_page=page, evaluation=evaluation,
                               run=folder.name if folder else None)

    @app.post('/dashboard/ai-training/export')
    @admin_required
    def export_training():
        kind = request.form.get('kind')
        if kind == 'dataset':
            try:
                records = read_dataset(app.config['TRAINING_DATA_PATH'])
            except (OSError, ValueError, UnicodeError):
                abort(404)
            columns = ['path', 'label', 'family']
        elif kind in {'v1', 'v2'}:
            metadata = inspect_models(predictor, app.config['EXPERIMENTAL_MODEL_PATH'])[kind]
            if metadata is None:
                abort(404)
            records, columns = metadata['weights'], ['feature', 'coefficient', 'train_mean', 'train_scale']
        else:
            abort(400)
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for row in records:
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v)
                             for k, v in row.items()})
        insert_security_event(app.config['DATABASE'], request.remote_addr or 'unknown', 'admin', 'training_csv_exported')
        return send_file(io.BytesIO(buffer.getvalue().encode('utf-8-sig')), as_attachment=True,
                         download_name=f'{kind}.csv', mimetype='text/csv')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'model_loaded': predictor is not None,
                'model_status': model_status}

    def evaluation_data(run=None):
        """Read only local evaluation artifacts; no model loading or training."""
        folder = Path(app.config['EVALUATION_ROOT'])
        try:
            if run is None:
                pointer = json.loads((folder / 'latest.json').read_text(encoding='utf-8'))
                run = pointer['run']
            if not isinstance(run, str) or not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{6}', run):
                return None, None
            run_dir = (folder / run).resolve()
            if not run_dir.is_relative_to(folder.resolve()):
                return None, None
            result_file = run_dir / 'results.json'
            if result_file.stat().st_size > 2 * 1024 * 1024:
                return None, None
            data = validate_evaluation(json.loads(result_file.read_text(encoding='utf-8')))
            return data, run_dir
        except (OSError, ValueError, KeyError, TypeError):
            return None, None

    @app.get('/dashboard/ai-evaluation')
    @admin_required
    def ai_evaluation():
        data, folder = evaluation_data(request.args.get('run'))
        return render_template('ai_evaluation.html', evaluation=data,
                               run=folder.name if folder else None,
                               history=evaluation_history(app.config['EVALUATION_ROOT']))

    @app.get('/dashboard/ai-evaluation/chart/<name>')
    @admin_required
    def ai_evaluation_chart(name):
        if name not in {'confusion_matrix.png', 'metrics.png', 'latency.png'}:
            abort(404)
        run = request.args.get('run')
        if not run:
            abort(404)
        data, folder = evaluation_data(run)
        # Serve the exact archived run referenced by the page, even if latest
        # changes between the HTML response and image requests.
        if not folder:
            abort(404)
        chart = (folder / name).resolve()
        if not chart.is_relative_to(folder) or not chart.is_file():
            abort(404)
        return send_file(chart, mimetype='image/png')

    return app
