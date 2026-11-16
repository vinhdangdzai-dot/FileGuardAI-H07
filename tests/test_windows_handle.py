import os
from pathlib import Path
import subprocess

import pytest
from app import security


@pytest.mark.skipif(os.name != 'nt', reason='Win32 handle boundary requires Windows')
def test_opened_handle_rejects_real_junction_swap(tmp_path, monkeypatch):
    base, outside = tmp_path / 'allowed', tmp_path / 'outside'
    race = base / 'race'
    race.mkdir(parents=True)
    outside.mkdir()
    (race / 'payload.txt').write_bytes(b'PUBLIC')
    secret = outside / 'payload.txt'
    secret.write_bytes(b'PRIVATE-DO-NOT-SERVE')
    original = security.safe_path
    changed = False

    def swap_after_check(root, raw):
        nonlocal changed
        result = original(root, raw)
        (race / 'payload.txt').unlink()
        race.rmdir()  # Only this owned, empty fixture directory.
        process = subprocess.run(['cmd', '/c', 'mklink', '/J', str(race), str(outside)], capture_output=True)
        if process.returncode:
            pytest.skip('Windows junction creation unavailable')
        changed = True
        return result

    monkeypatch.setattr(security, 'safe_path', swap_after_check)
    try:
        with pytest.raises(security.RejectedPath, match='Handle'):
            security.open_authorized(base, 'race/payload.txt')
        # A leaked open CRT handle would prevent this rename on Windows.
        secret.rename(outside / 'renamed.txt')
    finally:
        if changed:
            assert race.parent.resolve() == base.resolve()
            race.rmdir()


@pytest.mark.skipif(os.name != 'nt', reason='Win32 API failure check requires Windows')
def test_handle_query_failure_closes_file_and_rejects(tmp_path, monkeypatch):
    (tmp_path / 'ok.txt').write_bytes(b'PUBLIC')
    def fail(file):
        raise OSError('fixture: cannot query final handle path')
    monkeypatch.setattr(security, '_windows_opened_path', fail)
    with pytest.raises(security.RejectedPath):
        security.open_authorized(tmp_path, 'ok.txt')
    (tmp_path / 'ok.txt').rename(tmp_path / 'renamed.txt')
