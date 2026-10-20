"""Correos transaccionales (verificación y recuperación de contraseña) por SMTP.

El HTML vive en app/templates/email/ y se renderiza con Jinja2 (autoescape activo).
"""

import logging
from datetime import date
from functools import lru_cache

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from app.config import settings
from app.config.constants import TEMPLATES_DIR

logger = logging.getLogger(__name__)

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR / "email"), autoescape=select_autoescape(["html"]))


# Se crea en el primer envío: el API arranca aunque MAIL_* no esté configurado (p. ej. en tests)
@lru_cache
def _mailer() -> FastMail:
    return FastMail(
        ConnectionConfig(
            MAIL_USERNAME=settings.mail_username,
            MAIL_PASSWORD=settings.mail_password,
            MAIL_FROM=settings.mail_from,
            MAIL_PORT=settings.mail_port,
            MAIL_SERVER=settings.mail_server,
            MAIL_STARTTLS=settings.mail_starttls,
            MAIL_SSL_TLS=settings.mail_ssl_tls,
            USE_CREDENTIALS=settings.mail_use_credentials,
        )
    )


async def _send(to: EmailStr, subject: str, template: str, link: str) -> None:
    html = _env.get_template(template).render(link=link, year=date.today().year)
    await _mailer().send_message(MessageSchema(subject=subject, recipients=[to], body=html, subtype="html"))
    logger.info("Correo '%s' enviado a %s", template, to)


async def send_verification_email_gmail(to: EmailStr, verification_link: str) -> None:
    await _send(to, "🌿 Verifica tu correo electrónico - Appalta2", "verification.html", verification_link)


async def send_password_reset_email_gmail(to: EmailStr, reset_link: str) -> None:
    await _send(to, "Recupera tu contraseña - Appalta2", "password_reset.html", reset_link)
