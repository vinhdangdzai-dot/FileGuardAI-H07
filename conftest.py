"""Keep normal `python -m pytest` independent of Windows' shared temp root."""
import os
from pathlib import Path
import tempfile

import pytest
from tools.pytest_runtime import create_runtime, runtime_environment


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    runtime = create_runtime(Path(__file__).resolve().parent)
    # Explicit caller options remain caller-owned. Our default is always fresh.
    if config.option.basetemp is None:
        config.option.basetemp = str(runtime['basetemp'])
    config._h07_runtime_previous = (
        {key: os.environ.get(key) for key in ('TEMP', 'TMP', 'TMPDIR')}, tempfile.tempdir)
    env = runtime_environment(runtime)
    for key in ('TEMP', 'TMP', 'TMPDIR'):
        os.environ[key] = env[key]
    # tempfile may already have cached the system path during plugin loading.
    tempfile.tempdir = str(runtime['temporary'])


def pytest_unconfigure(config):
    previous = getattr(config, '_h07_runtime_previous', None)
    if previous is None:
        return
    env, cached = previous
    for key, value in env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    tempfile.tempdir = cached
