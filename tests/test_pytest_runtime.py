import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest
from tools.pytest_runtime import create_runtime, runtime_environment
from tools.run_h07_acceptance import pytest_counts

ROOT = Path(__file__).resolve().parents[1]


def test_fresh_basetemp_with_spaces_preserves_existing_files(tmp_path):
    workspace = tmp_path / 'workspace with spaces'
    workspace.mkdir()
    sentinel = workspace / 'important.txt'
    sentinel.write_text('must survive', encoding='utf-8')
    first = create_runtime(workspace)
    second = create_runtime(workspace)
    assert first['root'] != second['root']
    assert not first['basetemp'].exists()
    assert first['temporary'].is_dir()
    assert sentinel.read_text(encoding='utf-8') == 'must survive'
    env = runtime_environment(first, {'TEMP': 'inaccessible', 'PATH': 'preserved'})
    assert env['TEMP'] == env['TMP'] == env['TMPDIR'] == str(first['temporary'])
    assert env['PATH'] == 'preserved'


def test_allocation_never_uses_denied_default_temp(tmp_path, monkeypatch):
    def denied():
        raise PermissionError('simulated WinError 5: default TEMP denied')
    monkeypatch.setattr(tempfile, 'gettempdir', denied)
    runtime = create_runtime(tmp_path)
    assert not runtime['basetemp'].exists()


def test_denied_runtime_write_is_error_not_skip(tmp_path, monkeypatch):
    original = Path.mkdir
    def denied(path, *args, **kwargs):
        if path.name.startswith('.test_runtime_'):
            raise PermissionError('workspace itself not writable')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', denied)
    with pytest.raises(PermissionError, match='not writable'):
        create_runtime(tmp_path)


def test_owner_only_shared_runtime_is_not_reused(tmp_path, monkeypatch):
    shared = tmp_path / '.test_runtime'
    shared.mkdir()
    original = Path.mkdir
    def deny_shared(path, *args, **kwargs):
        if path == shared or shared in path.parents:
            raise PermissionError('old shared directory belongs to another account')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', deny_shared)
    runtime = create_runtime(tmp_path)
    assert runtime['root'].parent == tmp_path
    assert not runtime['basetemp'].exists()


@pytest.mark.parametrize('explicit_base', [False, True])
def test_subprocess_pytest_bypasses_denied_default_and_cache(tmp_path, explicit_base):
    # Real pytest subprocess; failure injection simulates unavailable default
    # pytest temp without editing ACLs or requiring administrator privileges.
    workspace = tmp_path / 'probe with spaces'
    workspace.mkdir()
    runtime = create_runtime(workspace)
    plugin = workspace / 'blocked_default.py'
    plugin.write_text('''import tempfile
from pathlib import Path
import _pytest.tmpdir
original = tempfile.gettempdir
def denied_user():
    raise PermissionError('default pytest-of-user denied')
_pytest.tmpdir.get_user = denied_user
def guarded_temp():
    if not tempfile.tempdir or '.test_runtime' not in str(tempfile.tempdir):
        raise PermissionError('default system TEMP denied')
    return original()
tempfile.gettempdir = guarded_temp
def pytest_configure(config):
    assert not config.pluginmanager.hasplugin('cacheprovider')
''', encoding='utf-8')
    probe = workspace / 'test_probe.py'
    probe.write_text('''import tempfile
from pathlib import Path
def test_probe(tmp_path):
    assert '.test_runtime' in str(tmp_path)
    (tmp_path/'ok.txt').write_text('ok')
    with tempfile.TemporaryDirectory() as temp:
        assert '.test_runtime' in str(Path(temp))
''', encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(workspace) + os.pathsep + str(ROOT),
               TEMP=str(workspace/'denied'), TMP=str(workspace/'denied'), TMPDIR=str(workspace/'denied'))
    options = ['--basetemp='+str(runtime['basetemp'])] if explicit_base else []
    completed = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'blocked_default',
                                *options, str(probe)], cwd=ROOT,
                               env=env, capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '1 passed' in completed.stdout
    assert 'PytestCacheWarning' not in completed.stdout + completed.stderr


def test_junit_distinguishes_fail_error_skip(tmp_path):
    path = tmp_path/'results.xml'
    path.write_text('<testsuites><testsuite><testcase/><testcase><failure/></testcase>'
                    '<testcase><error/></testcase><testcase><skipped/></testcase></testsuite></testsuites>')
    assert pytest_counts(path) == dict(PASS=1, FAIL=1, ERROR=1, SKIP=1)
