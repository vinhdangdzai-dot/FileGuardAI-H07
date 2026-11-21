from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEPLOY=ROOT/'deploy/ubuntu'


def text(name):
    return (DEPLOY/name).read_text(encoding='utf-8')


def test_production_service_is_loopback_non_root_and_factory_based():
    unit=text('canhgacso.service')
    assert 'User=deploy' in unit and 'User=root' not in unit
    assert '--bind 127.0.0.1:8000' in unit
    assert 'app:create_app()' in unit and '--preload' not in unit
    assert 'EnvironmentFile=/etc/canhgacso/canhgacso.env' in unit


def test_nginx_overwrites_forwarded_ip_and_does_not_expose_private_files():
    nginx=text('nginx.conf')
    assert 'proxy_pass http://127.0.0.1:8000' in nginx
    assert 'proxy_set_header X-Forwarded-For $remote_addr;' in nginx
    assert '$proxy_add_x_forwarded_for' not in nginx
    assert 'instance(?:/|$)' in nginx and 'artifacts(?:/|$)' in nginx and 'deny all;' in nginx
    assert '.well-known' in nginx


def test_deploy_templates_contain_no_secret_and_updates_do_not_train_or_force_push():
    combined='\n'.join(p.read_text(encoding='utf-8') for p in DEPLOY.iterdir() if p.is_file())
    assert 'AI_EXPLANATION_API_KEY=\n' in combined
    assert 'SECRET_KEY=\n' in combined
    assert 'git push --force' not in combined
    update=text('update.sh')
    assert 'ml.train_model' not in update and 'merge --ff-only' in update
    assert '.backup' in update and 'canhgacso.env' in update


def test_artifact_restore_is_hash_pinned_and_refuses_overwrite():
    script=text('restore_artifacts.sh').lower()
    assert '4d7324aa302ecb3d1b731561210a0041e4aef3f740cc68d9187097a80e5a6322' in script
    assert '2a2f427ddf77c27815839a29ec9fbf0448feeb7ad1b4a9675cff56e0166182d0' in script
    assert 'refusing to overwrite' in script
