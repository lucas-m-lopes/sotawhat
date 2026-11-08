# sotawhat/notify/email.py
"""E-mail copy of the digest over SMTP: STARTTLS on 587, implicit TLS on 465.

With Gmail it needs an app password (myaccount.google.com/apppasswords, with 2-Step Verification on):
Google refuses the account password over SMTP (534 5.7.9), so a secret that does not look like an app
password stops here, before any connection, and the account password is never sent. Error messages
never contain the secret."""
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

GMAIL_HOSTS = ("smtp.gmail.com", "smtp.googlemail.com")
APP_PASSWORD_HINT = ("use uma senha de app do Google (16 letras) em GMAIL_APP_PASSWORD, criada em "
                     "https://myaccount.google.com/apppasswords; nunca a senha normal da conta")


class EmailError(Exception):
    pass


def looks_like_app_password(secret) -> bool:
    """Google app passwords are 16 lowercase letters, shown in groups of four."""
    return re.fullmatch(r"[a-z]{16}", "".join((secret or "").split())) is not None


def _close(server, polite=True) -> None:
    if server is None:
        return
    try:
        server.quit() if polite else server.close()
    except Exception:  # noqa: BLE001 - the connection is going away anyway
        try:
            server.close()
        except Exception:  # noqa: BLE001
            pass


class EmailNotifier:
    def __init__(self, host, port, user, password, sender=None, timeout=30,
                 smtp=smtplib.SMTP, smtp_ssl=smtplib.SMTP_SSL):
        self.host, self.port, self.user = host, int(port), user
        self.sender = sender or user
        self.timeout = timeout
        self._password = password or ""
        self._smtp, self._smtp_ssl = smtp, smtp_ssl

    @property
    def gmail(self) -> bool:
        return self.host.lower() in GMAIL_HOSTS

    def _secret(self) -> str:
        return "".join(self._password.split()) if self.gmail else self._password

    def _clean(self, text) -> str:
        secret = self._secret()
        return str(text).replace(secret, "***") if secret else str(text)

    def _connect(self):
        if not (self.user and self._password):
            raise EmailError("SMTP sem usuário ou senha (GMAIL_ADDRESS/GMAIL_APP_PASSWORD ou SMTP_USER/SMTP_PASSWORD)")
        if self.gmail and not looks_like_app_password(self._password):
            raise EmailError("GMAIL_APP_PASSWORD não parece uma senha de app: " + APP_PASSWORD_HINT)
        context = ssl.create_default_context()
        server = None
        try:
            if self.port == 465:
                server = self._smtp_ssl(self.host, self.port, timeout=self.timeout, context=context)
            else:
                server = self._smtp(self.host, self.port, timeout=self.timeout)
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(self.user, self._secret())
            return server
        except smtplib.SMTPAuthenticationError as exc:
            _close(server, polite=False)
            detail = exc.smtp_error.decode("utf-8", "replace") if isinstance(exc.smtp_error, bytes) else exc.smtp_error
            hint = f"; {APP_PASSWORD_HINT}" if self.gmail else ""
            raise EmailError(self._clean(f"login SMTP recusado ({exc.smtp_code} {str(detail).strip()}){hint}")) from None
        except (smtplib.SMTPException, OSError) as exc:
            _close(server, polite=False)
            raise EmailError(self._clean(f"SMTP {self.host}:{self.port}: {type(exc).__name__}: {exc}")) from None

    def check_login(self) -> None:
        """Connect and authenticate, send nothing (used by `sotawhat doctor`)."""
        _close(self._connect())

    def send(self, to, subject, text, html=None) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=self.sender.rsplit("@", 1)[-1] if "@" in self.sender else "sotawhat")
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        server = self._connect()
        try:
            server.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailError(self._clean(f"envio SMTP falhou: {type(exc).__name__}: {exc}")) from None
        finally:
            _close(server)


def from_settings(settings) -> EmailNotifier:
    return EmailNotifier(settings.smtp_host, settings.smtp_port, settings.smtp_login, settings.smtp_secret)
