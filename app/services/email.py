"""Correos transaccionales (verificación y recuperación de contraseña) por SMTP.

El HTML vive en app/templates/email/ y se renderiza con Jinja2 (autoescape activo).
"""

import logging
from datetime import date

from fastapi_mail import FastMail, MessageSchema
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from app.config.config import TEMPLATES_DIR, mail_conf

logger = logging.getLogger(__name__)

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR / "email"), autoescape=select_autoescape(["html"]))
_mailer = FastMail(mail_conf)


async def _send(to: EmailStr, subject: str, template: str, link: str) -> None:
    html = _env.get_template(template).render(link=link, year=date.today().year)
    await _mailer.send_message(MessageSchema(subject=subject, recipients=[to], body=html, subtype="html"))
    logger.info("Correo '%s' enviado a %s", template, to)


async def send_verification_email_gmail(to: EmailStr, verification_link: str) -> None:
    await _send(to, "🌿 Verifica tu correo electrónico - Appalta2", "verification.html", verification_link)


async def send_password_reset_email_gmail(to: EmailStr, reset_link: str) -> None:
    await _send(to, "Recupera tu contraseña - Appalta2", "password_reset.html", reset_link)
