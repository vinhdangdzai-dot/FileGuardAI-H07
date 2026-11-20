"""Recovery SMTP must encrypt before authentication or message delivery."""
from types import SimpleNamespace

import pytest

from app.account_mail import RecoveryMail


@pytest.mark.parametrize('implicit_tls', [False, True])
def test_smtp_requires_tls_before_credentials_and_message(monkeypatch, implicit_tls):
    calls = []

    class Transport:
        def __init__(self, host, port, **kwargs):
            calls.append(('connect', host, port, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append(('close',))

        def starttls(self, **kwargs):
            calls.append(('tls', kwargs))

        def login(self, username, password):
            calls.append(('auth',))

        def send_message(self, message):
            calls.append(('send',))
            assert message['To'] == 'user@example.test'
            assert '#token=' in message.get_content()

    monkeypatch.setattr('app.account_mail.smtplib.SMTP_SSL', Transport)
    monkeypatch.setattr('app.account_mail.smtplib.SMTP', Transport)
    service = RecoveryMail.__new__(RecoveryMail)
    service.app = SimpleNamespace(config={
        'ACCOUNT_SMTP_HOST': 'smtp.example.test', 'ACCOUNT_SMTP_PORT': 465 if implicit_tls else 587,
        'ACCOUNT_SMTP_FROM': 'recovery@example.test', 'ACCOUNT_SMTP_SSL': implicit_tls,
        'ACCOUNT_SMTP_USERNAME': 'mailer', 'ACCOUNT_SMTP_PASSWORD': 'mock-only',
    })
    service.smtp_send('user@example.test', 'https://example.test/reset-password#token=mock-only')
    assert [call[0] for call in calls] == (['connect', 'auth', 'send', 'close'] if implicit_tls else ['connect', 'tls', 'auth', 'send', 'close'])
    assert calls[0][3]['timeout'] == 5
    context = calls[0][3]['context'] if implicit_tls else calls[1][1]['context']
    assert context.check_hostname and context.verify_mode.name == 'CERT_REQUIRED'


def test_starttls_failure_never_authenticates_or_sends(monkeypatch):
    calls = []

    class Transport:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            raise OSError('mock TLS failure')

        def login(self, *args):
            calls.append('auth')

        def send_message(self, *args):
            calls.append('send')

    monkeypatch.setattr('app.account_mail.smtplib.SMTP', Transport)
    service = RecoveryMail.__new__(RecoveryMail)
    service.app = SimpleNamespace(config={
        'ACCOUNT_SMTP_HOST': 'smtp.example.test', 'ACCOUNT_SMTP_PORT': 587,
        'ACCOUNT_SMTP_FROM': 'recovery@example.test', 'ACCOUNT_SMTP_SSL': False,
        'ACCOUNT_SMTP_USERNAME': 'mailer', 'ACCOUNT_SMTP_PASSWORD': 'mock-only',
    })
    with pytest.raises(OSError):
        service.smtp_send('user@example.test', 'https://example.test/reset-password#token=mock-only')
    assert calls == []
