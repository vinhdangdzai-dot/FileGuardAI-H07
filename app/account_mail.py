"""Bounded recovery delivery. No token/body/recipient is logged or persisted here."""
from contextlib import closing
from email.message import EmailMessage
import queue
import smtplib
import ssl
import threading
from urllib.parse import urlsplit
from .database import connect
from .account_store import audit


class RecoveryMail:
    def __init__(self,app):
        self.app=app;self.queue=queue.Queue(maxsize=16);self.stop=threading.Event();self.thread=None
        origin=app.config.get('ACCOUNT_RESET_ORIGIN') or ''
        parsed=urlsplit(origin)
        valid=bool(parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and
                   (parsed.scheme=='https' or (app.testing and parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1'})))
        self.origin=origin.rstrip('/') if valid else None
        self.sender=app.config.get('ACCOUNT_MAIL_SENDER')
        if self.sender is None and not app.testing and all(app.config.get(k) for k in ('ACCOUNT_SMTP_HOST','ACCOUNT_SMTP_FROM')):
            self.sender=self.smtp_send
        self.configured=bool(self.origin and self.sender)
        if self.configured:
            self.thread=threading.Thread(target=self.run,daemon=True,name='account-recovery-mail');self.thread.start()

    def smtp_send(self,address,url):
        cfg=self.app.config
        message=EmailMessage();message['Subject']='CANH GÁC SỐ — Đặt lại mật khẩu'
        message['From']=cfg['ACCOUNT_SMTP_FROM'];message['To']=address
        message.set_content('Bạn đã yêu cầu đặt lại mật khẩu. Liên kết dùng một lần, hết hạn sau 15 phút:\n'+url+'\nNếu không yêu cầu, hãy bỏ qua email này.')
        context=ssl.create_default_context()
        if cfg.get('ACCOUNT_SMTP_SSL'):
            smtp=smtplib.SMTP_SSL(cfg['ACCOUNT_SMTP_HOST'],cfg['ACCOUNT_SMTP_PORT'],timeout=5,context=context)
        else:
            smtp=smtplib.SMTP(cfg['ACCOUNT_SMTP_HOST'],cfg['ACCOUNT_SMTP_PORT'],timeout=5)
        with smtp:
            if not cfg.get('ACCOUNT_SMTP_SSL'):smtp.starttls(context=context)
            if cfg.get('ACCOUNT_SMTP_USERNAME'):smtp.login(cfg['ACCOUNT_SMTP_USERNAME'],cfg.get('ACCOUNT_SMTP_PASSWORD') or '')
            smtp.send_message(message)

    def submit(self,address,token,digest):
        if not self.configured:return False
        try:self.queue.put_nowait((address,self.origin+'/reset-password#token='+token,digest));return True
        except queue.Full:return False

    def run(self):
        while not self.stop.is_set():
            try:address,url,digest=self.queue.get(timeout=.2)
            except queue.Empty:continue
            try:
                self.sender(address,url)
                event='password_reset_delivery_sent'
            except Exception:
                event='password_reset_delivery_failed'
                try:
                    with closing(connect(self.app.config['DATABASE'])) as db,db:db.execute('UPDATE auth_reset_tokens SET used=1 WHERE digest=?',(digest,))
                except Exception:pass
            finally:
                try:
                    with closing(connect(self.app.config['DATABASE'])) as db,db:audit(db,'local','system',event)
                except Exception:pass
                self.queue.task_done()

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1)
