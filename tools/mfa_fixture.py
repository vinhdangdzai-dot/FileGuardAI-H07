"""Authenticator for owned localhost verification fixtures; no application bypass.

Secrets/codes remain in the verifier's memory, never evidence or application DB.
The verifier reads the same password-protected setup page available to the owner.
"""
import re
import time
from urllib.parse import urlsplit

import pyotp


class Authenticator:
    def __init__(self):
        self.secret = None
        self.codes = []
        self.last_counter = -1

    def factor(self, html):
        match = re.search(r'id="mfa-secret">([A-Z2-7]+)</code>', html)
        if match:
            self.secret = match[1]
        elif self.codes:
            return self.codes.pop()
        if not self.secret:
            raise RuntimeError('Fixture authenticator has not been enrolled')
        instant = time.time()
        # Use real wall-clock TOTP. Avoid both replay and a network trip at rollover.
        counter = int(instant // 30)
        if counter <= self.last_counter or instant % 30 > 28:
            time.sleep(30 - instant % 30 + .1)
        self.last_counter = int(time.time() // 30)
        return pyotp.TOTP(self.secret).now()

    def remember(self, html):
        codes = re.findall(r'<li><code>([0-9a-f-]{35})</code>', html)
        if codes:
            if len(codes) != 8:
                raise RuntimeError('Incomplete fixture recovery-code response')
            self.codes = codes


_BROWSERS = {}


def complete_browser(page):
    page.wait_for_load_state('networkidle')
    parsed = urlsplit(page.url)
    if parsed.path != '/login/mfa':
        return
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise RuntimeError('Browser authenticator is restricted to localhost fixtures')
    key = parsed.scheme + '://' + parsed.netloc
    verifier = _BROWSERS.setdefault(key, Authenticator())
    factor = verifier.factor(page.content())
    page.locator('#mfa-code').fill(factor)
    page.locator('.account-panel form[data-navigation-form] button').click()
    page.wait_for_load_state('networkidle')
    if page.locator('#mfa-backup-codes').count():
        verifier.remember(page.content())
        page.locator('a[href="/dashboard"]').last.click()
    page.wait_for_url('**/dashboard')
    page.wait_for_load_state('networkidle')
