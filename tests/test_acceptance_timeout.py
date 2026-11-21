"""A timed-out suite retains evidence and cannot turn into acceptance success."""
import json
import subprocess

from tools import run_h07_acceptance as runner


def test_timeout_is_error_preserves_output_and_runs_other_suites(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime' / 'pytest'
    runtime.mkdir(parents=True)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1:3] == ['-m', 'pytest']:
            raise subprocess.TimeoutExpired(command, kwargs['timeout'], output=b'partial test output', stderr=b'partial diagnostic')
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'create_runtime', lambda *args: {'basetemp': runtime})
    monkeypatch.setattr(runner, 'runtime_environment', lambda *args: {})
    monkeypatch.setattr(runner.subprocess, 'run', run)
    assert runner.main() == 1
    assert len(calls) == 6
    folder = next((tmp_path / 'docs' / 'bao_cao_h07' / 'evidence').iterdir())
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    result = summary['steps']['pytest']
    assert result['returncode'] == 124 and result['status'] == 'ERROR'
    assert result['reason'] == 'process_timeout' and 'junit_counts' not in result
    assert (folder / 'pytest.stdout.txt').read_text(encoding='utf-8') == 'partial test output'
    assert (folder / 'pytest.stderr.txt').read_text(encoding='utf-8') == 'partial diagnostic'
