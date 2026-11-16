from pathlib import Path
from urllib.parse import quote

import pytest
pytest.importorskip("flask", reason="Flask is installed by requirements.txt on the user machine")

from app import create_app
from app.database import recent_logs


@pytest.fixture
def client(tmp_path):
    base = tmp_path / 'allowed'
    base.mkdir()
    (base / 'tailieu').mkdir()
    (base / 'baocao.pdf').write_bytes(b'%PDF-1.4\nfixture')
    (base / 'báo cáo tốt nghiệp.pdf').write_bytes(b'viet nam')
    (base / 'tailieu' / 'chuong1.pdf').write_bytes(b'chuong1')
    (tmp_path / 'secret.txt').write_bytes(b'SECRET-DO-NOT-SERVE')
    app = create_app({
        'TESTING': True, 'FILES_ROOT': base,
        'DATABASE': tmp_path / 'events.sqlite3',
        'MODEL_PATH': tmp_path / 'nonexistent-model.joblib',
        'ADMIN_PASSWORD': 'test-only-secret',
    })
    return app.test_client(), app, tmp_path


def test_valid_downloads(client):
    c, app, tmp = client
    for name in ['baocao.pdf', 'báo cáo tốt nghiệp.pdf', 'tailieu/chuong1.pdf']:
        response = c.get('/download', query_string={'path': name})
        assert response.status_code == 200
        assert response.data
        assert 'attachment' in response.headers['Content-Disposition']


def test_no_traversal_or_symlink_escape(client):
    c, app, tmp = client
    bad = ['../secret.txt', '../../config.txt', '..\\secret.txt', '/etc/passwd', 'C:\\Windows\\win.ini']
    for p in bad:
        response = c.get('/download', query_string={'path': p})
        assert response.status_code == 403, p
        assert b'SECRET-DO-NOT-SERVE' not in response.data
    link = app.config['FILES_ROOT'] / 'link.txt'
    try:
        link.symlink_to(tmp / 'secret.txt')
    except OSError:
        pytest.skip('Windows requires symlink privilege or Developer Mode')
    else:
        assert c.get('/download', query_string={'path': 'link.txt'}).status_code == 403


def test_encoded_traversal(client):
    c, app, tmp = client
    # Flask will decode this query parameter exactly once.
    response = c.get('/download?path=..%2Fsecret.txt')
    assert response.status_code == 403
    # Residual structural escapes violate policy without another decode.
    response = c.get('/download?path=..%252Fsecret.txt')
    assert response.status_code == 403
    assert b'SECRET-DO-NOT-SERVE' not in response.data


def test_missing_file_and_log(client):
    c, app, tmp = client
    assert c.get('/download', query_string={'path': 'notfound.txt'}).status_code == 404
    assert c.get('/download', query_string={'path': '../secret.txt'}).status_code == 403
    logs = recent_logs(app.config['DATABASE'])
    assert len(logs) == 2
    assert logs[0]['action'] == 'BLOCK'
    assert logs[0]['ml_label'] == 'unavailable'


def test_admin_dashboard_restricted(client):
    c, app, tmp = client
    assert c.get('/dashboard').status_code == 302
    bad_login = c.post('/login', data={'password': 'bad'})
    assert bad_login.status_code == 200
    good_login = c.post('/login', data={'password': 'test-only-secret'})
    assert good_login.status_code == 302
    assert c.get('/dashboard').status_code == 200
    assert c.post('/logout').status_code == 302
    assert c.get('/dashboard').status_code == 302


class AlwaysBenignModel:
    """Simulated ML false negative: always returns 99% benign."""
    def predict_proba(self, features):
        return [[0.99, 0.01] for _ in features]


def test_false_negative_ai_cannot_bypass_policy(client, tmp_path):
    import joblib
    c, app, root = client
    model_path = tmp_path / 'fake_model.joblib'
    joblib.dump(AlwaysBenignModel(), model_path)
    app2 = create_app({
        'TESTING': True, 'FILES_ROOT': app.config['FILES_ROOT'],
        'DATABASE': tmp_path / 'events_false_negative.sqlite3',
        'MODEL_PATH': model_path, 'ADMIN_PASSWORD': 'test-only-secret',
    })
    response = app2.test_client().get('/download', query_string={'path': '../secret.txt'})
    assert response.status_code == 403
    event = recent_logs(app2.config['DATABASE'])[0]
    assert event['ml_label'] == 'benign'  # AI failed, security still holds.
    assert event['action'] == 'BLOCK'


@pytest.mark.parametrize('payload', [
    '%2e%2e%2fsecret.txt', '%2E%2e%5Csecret.txt',
    '%252e%252e%252fsecret.txt', '%25252e%25252e%25252fsecret.txt',
    'tailieu/%2e%2e/secret.txt', '%2fetc/passwd',
    'C%3a%5cWindows%5cwin.ini', '%00secret.txt',
    '../../windows/win.ini', '\\\\server\\share\\secret.txt',
])
def test_form_encoded_payloads_are_blocked(client, payload):
    c, app, tmp = client
    # query_string reproduces browser form encoding, including % -> %25.
    with c.get('/download', query_string={'path': payload}) as response:
        assert response.status_code == 403
        assert b'SECRET-DO-NOT-SERVE' not in response.data
    event = recent_logs(app.config['DATABASE'])[0]
    assert (event['action'], event['http_status']) == ('BLOCK', 403)
    assert event['requested_path'] == payload


@pytest.mark.parametrize('query', [
    '%2e%2e%2fsecret.txt', '%2E%2E%5Csecret.txt',
    '%252e%252e%252fsecret.txt', '%25252e%25252e%25252fsecret.txt',
    '%2fetc%2fpasswd', 'C%3a%5cWindows%5cwin.ini',
])
def test_raw_url_payloads_are_blocked(client, query):
    c, app, tmp = client
    with c.get('/download?path=' + query) as response:
        assert response.status_code == 403
        assert b'SECRET-DO-NOT-SERVE' not in response.data


@pytest.mark.parametrize('name', [
    'tài liệu/báo cáo tốt nghiệp.txt', '100% hoàn thành.txt',
    'literal%20name.txt', 'a+b.txt',
])
def test_exact_filename_bytes_and_no_extra_decode(client, name):
    c, app, tmp = client
    target = app.config['FILES_ROOT'] / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'EXACT-CONTENT')
    # One URL decode must preserve literal %, +, Unicode and spaces.
    with c.get('/download?path=' + quote(name, safe='')) as response:
        assert response.status_code == 200
        assert response.data == b'EXACT-CONTENT'
    event = recent_logs(app.config['DATABASE'])[0]
    assert event['requested_path'] == name
    assert event['action'] == 'ALLOW'


class AlwaysSuspiciousModel:
    def predict_proba(self, features):
        return [[0.0, 1.0] for _ in features]


def test_high_ai_score_does_not_decide_access(client, tmp_path):
    import joblib
    c, original, tmp = client
    model_path = tmp_path / 'suspicious.joblib'
    joblib.dump(AlwaysSuspiciousModel(), model_path)
    config = dict(original.config)
    config.update(MODEL_PATH=model_path, DATABASE=tmp_path / 'ai.sqlite3')
    app = create_app(config)
    c = app.test_client()
    for name, status, action in [
        ('baocao.pdf', 200, 'ALLOW'), ('missing.txt', 404, 'MISS'),
        ('../secret.txt', 403, 'BLOCK'),
    ]:
        with c.get('/download', query_string={'path': name}) as response:
            assert response.status_code == status
        event = recent_logs(app.config['DATABASE'])[0]
        assert event['ml_score'] == 1.0
        assert event['ml_label'] == 'suspicious'
        assert event['action'] == action


def test_windows_junction_escape(client):
    import subprocess
    import os
    if os.name != 'nt':
        pytest.skip('Windows junction test')
    c, app, tmp = client
    junction = app.config['FILES_ROOT'] / 'junction'
    result = subprocess.run(
        ['cmd', '/c', 'mklink', '/J', str(junction), str(tmp)],
        capture_output=True,
    )
    if result.returncode:
        pytest.skip('Junction creation unavailable: ' + repr(result.stderr))
    try:
        for name in ['junction/secret.txt', 'junction/missing.txt']:
            with c.get('/download', query_string={'path': name}) as response:
                assert response.status_code == 403
                assert b'SECRET-DO-NOT-SERVE' not in response.data
        assert 'junction/secret.txt' not in c.get('/').get_data(as_text=True)
    finally:
        # Remove just the junction, never its target or contents.
        junction.rmdir()


def test_shipped_logistic_regression_integration(client, tmp_path):
    from sklearn.linear_model import LogisticRegression
    import joblib
    model_path = Path(__file__).resolve().parents[1] / 'artifacts/model.joblib'
    assert model_path.is_file(), 'Expected project model artifact'
    model = joblib.load(model_path)
    assert isinstance(model.named_steps['model'], LogisticRegression)
    c, original, tmp = client
    config = dict(original.config)
    config.update(MODEL_PATH=model_path, DATABASE=tmp_path / 'real_model.sqlite3')
    app = create_app(config)
    c = app.test_client()
    for name, status in [('baocao.pdf', 200), ('missing.txt', 404),
                         ('%2e%2e%2fsecret.txt', 403)]:
        with c.get('/download', query_string={'path': name}) as response:
            assert response.status_code == status
        event = recent_logs(app.config['DATABASE'])[0]
        assert 0 <= event['ml_score'] <= 1
        assert event['ml_label'] in {'benign', 'suspicious'}
