"""H07 Path Traversal Lab – Flask application factory."""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import time
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .database import init_db, insert_log, recent_logs, summary
from .ml_features import extract_features, simple_rule
from .security import RejectedPath, list_allowed_files, open_authorized

BASE = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        FILES_ROOT=BASE / 'shared_files',
        DATABASE=BASE / 'instance' / 'events.sqlite3',
        MODEL_PATH=BASE / 'artifacts' / 'model.joblib',
        EVALUATION_ROOT=BASE / 'docs' / 'evaluations',
        ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(12),
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    if config:
        app.config.update(config)
    if app.config.get('TESTING') and 'ADMIN_PASSWORD' not in (config or {}):
        app.config['ADMIN_PASSWORD'] = 'test-only-secret'
    app.config['ADMIN_HASH'] = generate_password_hash(app.config['ADMIN_PASSWORD'])

    root = Path(app.config['FILES_ROOT'])
    root.mkdir(parents=True, exist_ok=True)
    init_db(Path(app.config['DATABASE']))

    predictor = None
    model_path = Path(app.config['MODEL_PATH'])
    if model_path.exists():
        import joblib
        # Only load locally produced artifacts; joblib is pickle-based.
        predictor = joblib.load(model_path)

    def score_path(text):
        if predictor is None:
            return None, 'unavailable'
        try:
            probability = float(predictor.predict_proba([extract_features(text)])[0][1])
            return probability, ('suspicious' if probability >= 0.5 else 'benign')
        except (ValueError, TypeError):
            return None, 'error'

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get('is_admin'):
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

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
            action, status, reason = 'BLOCK', 403, str(exc)
            response = render_template('error.html', code=403, message=reason), 403
        except (FileNotFoundError, NotADirectoryError):
            action, status, reason = 'MISS', 404, 'Không tìm thấy tệp'
            response = render_template('error.html', code=404, message=reason), 404
        except OSError:
            action, status, reason = 'BLOCK', 403, 'Yêu cầu không thể truy cập'
            response = render_template('error.html', code=403, message=reason), 403
        insert_log(app.config['DATABASE'], ip, raw, score, ml_label,
                   action, status, reason, (time.perf_counter() - start) * 1000)
        return response

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            if check_password_hash(app.config['ADMIN_HASH'], request.form.get('password', '')):
                session.clear()
                session['is_admin'] = True
                return redirect(url_for('dashboard'))
            flash('Sai mật khẩu quản trị.')
        return render_template('login.html')

    @app.post('/logout')
    @admin_required
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.get('/dashboard')
    @admin_required
    def dashboard():
        logs = recent_logs(app.config['DATABASE'])
        counts = summary(app.config['DATABASE'])
        return render_template('dashboard.html', logs=logs, counts=counts)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'model_loaded': predictor is not None}

    def evaluation_data():
        """Read only local evaluation artifacts; no model loading or training."""
        folder = Path(app.config['EVALUATION_ROOT'])
        try:
            pointer = json.loads((folder / 'latest.json').read_text(encoding='utf-8'))
            run = pointer['run']
            if not isinstance(run, str) or not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{6}', run):
                return None, None
            run_dir = (folder / run).resolve()
            if not run_dir.is_relative_to(folder.resolve()):
                return None, None
            data = json.loads((run_dir / 'results.json').read_text(encoding='utf-8'))
            for key in ('audit', 'logistic_regression', 'regex', 'timing', 'test_samples', 'train_samples', 'created_at_utc'):
                if key not in data:
                    return None, None
            return data, run_dir
        except (OSError, ValueError, KeyError, TypeError):
            return None, None

    @app.get('/dashboard/ai-evaluation')
    @admin_required
    def ai_evaluation():
        data, folder = evaluation_data()
        return render_template('ai_evaluation.html', evaluation=data,
                               run=folder.name if folder else None)

    @app.get('/dashboard/ai-evaluation/chart/<name>')
    @admin_required
    def ai_evaluation_chart(name):
        if name not in {'confusion_matrix.png', 'metrics.png', 'latency.png'}:
            abort(404)
        data, folder = evaluation_data()
        # Pin chart requests to the run displayed by the page, even if a new
        # evaluation finishes between HTML and image requests.
        if not folder or request.args.get('run') != folder.name:
            abort(404)
        chart = (folder / name).resolve()
        if not chart.is_relative_to(folder) or not chart.is_file():
            abort(404)
        return send_file(chart, mimetype='image/png')

    return app
