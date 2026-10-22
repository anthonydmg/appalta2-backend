import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.config.constants import TEMPLATES_DIR
from app.database import user as user_db
from app.database.connection import get_db
from app.schemas import user as user_schemas
from app.services import auth
from app.services.email import send_password_reset_email_gmail, send_verification_email_gmail
from app.services.rate_limit import email_limiter, login_limiter

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

PUBLIC_API_URL = settings.public_api_url  # enlaces de los correos: {PUBLIC_API_URL}/v1/user/...
RESET_TOKEN_TTL = timedelta(hours=1)

# Respuestas idénticas exista o no la cuenta: no revelan qué correos están registrados
RESEND_MESSAGE = "Si el correo está registrado y pendiente de verificación, te enviaremos un nuevo enlace."
FORGOT_MESSAGE = "Si el correo está registrado, te enviaremos un enlace de recuperación."

def _verification_link(token: str) -> str:
    return f"{PUBLIC_API_URL}/v1/user/verify/{token}"

def _issue_tokens(user) -> user_schemas.Token:
    claims = {"sub": user.email}
    return user_schemas.Token(
        access_token=auth.create_access_token(claims),
        refresh_token=auth.create_refresh_token(claims),
        user_info=user_schemas.UserInfo.from_user(user),
    )

def _reset_token_expired(user) -> bool:
    expiry = user.reset_password_token_expiry
    if expiry is None:
        return True
    if expiry.tzinfo is None:  # columna sin zona horaria: se guarda en UTC
        expiry = expiry.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expiry

def _too_many_attempts(retry_after: int) -> HTTPException:
    minutes = max(1, round(retry_after / 60))
    return HTTPException(
        status_code=429,
        detail=f"Demasiados intentos. Vuelve a intentarlo en {minutes} min.",
        headers={"Retry-After": str(retry_after)},
    )

@router.get("/")
def root():
    return {"service": "API Appalta2", "version": "1.0.0", "status": "running"}


@router.post("/user/register", response_model=user_schemas.UserResponse)
def register(user: user_schemas.UserCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    if user_db.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if user_db.get_user_by_document(db, user.document_of_identity):
        raise HTTPException(status_code=400, detail="El número de DNI ya está registrado")

    verification_token = str(uuid.uuid4())
    try:
        db_user = user_db.create_user(db, user, verification_token)
    except IntegrityError:
        # Dos registros simultáneos con el mismo DNI o correo: la restricción UNIQUE de la BD decide.
        db.rollback()
        raise HTTPException(status_code=400, detail="El número de DNI o el correo ya está registrado")

    # En al envio del correo se realiza en segundo plago sin interrumpir el proceso del registro
    background.add_task(send_verification_email_gmail, user.email, _verification_link(verification_token))
    return db_user


@router.post("/user/login", response_model=user_schemas.Token)
def login(user: user_schemas.UserLogin, db: Session = Depends(get_db)):
    if retry_after := login_limiter.retry_after(user.email):
        raise _too_many_attempts(retry_after)

    db_user = user_db.autenticate_user(db, user.email, user.password)
    if not db_user:
        login_limiter.hit(user.email)
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    login_limiter.reset(user.email.lower())
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Correo no verificado")
    return _issue_tokens(db_user)


@router.post("/user/refresh", response_model=user_schemas.Token)
def refresh_token(refresh_token: str = Body(...), db: Session = Depends(get_db)):
    payload = auth.decode_token(refresh_token, auth.REFRESH)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token invalido")
    db_user = user_db.get_user_by_email(db, payload["sub"])
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if auth.issued_before(payload, db_user.password_changed_at):
        # La contraseña cambió después de iniciar esta sesión: hay que volver a ingresar
        raise HTTPException(status_code=401, detail="Sesión expirada")
    return _issue_tokens(db_user)


@router.get("/user/me", response_model=user_schemas.UserResponse)
def get_me(email: str = Depends(auth.verify_token), db: Session = Depends(get_db)):
    user = user_db.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("/user/verify/{token}", response_class=HTMLResponse)
def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = user_db.get_user_by_token(db, token)
    if not user:
        return templates.TemplateResponse(request=request, name="invalid_link.html", status_code=404)

    user.is_verified = True
    user.verification_token = None
    db.commit()
    return templates.TemplateResponse(request=request, name="verified.html")


@router.post("/user/resend-verification")
def resend_verification(
    req: user_schemas.ResendVerificationRequest, background: BackgroundTasks, db: Session = Depends(get_db)
):
    user = user_db.get_user_by_email(db, req.email)
    if user and not user.is_verified and not email_limiter.retry_after(req.email):
        email_limiter.hit(req.email)
        user.verification_token = str(uuid.uuid4())
        db.commit()
        background.add_task(send_verification_email_gmail, user.email, _verification_link(user.verification_token))
    return {"message": RESEND_MESSAGE}


@router.post("/user/password/forgot")
def forgot_password(req: user_schemas.ResetRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    user = user_db.get_user_by_email(db, req.email)
    if user and not email_limiter.retry_after(req.email):
        email_limiter.hit(req.email)
        user.reset_password_token = str(uuid.uuid4())
        user.reset_password_token_expiry = datetime.now(timezone.utc) + RESET_TOKEN_TTL
        db.commit()
        link = f"{PUBLIC_API_URL}/v1/user/reset/{user.reset_password_token}"
        background.add_task(send_password_reset_email_gmail, user.email, link)
    return {"message": FORGOT_MESSAGE}


@router.get("/user/reset/{token}", response_class=HTMLResponse)
def serve_reset_page(token: str, request: Request, db: Session = Depends(get_db)):
    user = user_db.get_user_by_reset_password_token(db, token)
    if not user or _reset_token_expired(user):
        return templates.TemplateResponse(request=request, name="invalid_link.html")
    return templates.TemplateResponse(request=request, name="reset_password.html", context={"token": token})

@router.post("/user/password/reset")
def reset_password(req: user_schemas.ResetPassword, db: Session = Depends(get_db)):
    user = user_db.get_user_by_reset_password_token(db, req.token)
    if not user or _reset_token_expired(user):
        raise HTTPException(status_code=400, detail="Token inválido o expirado.")

    user.hashed_password = auth.hash_password(req.new_password)
    user.password_changed_at = datetime.now(timezone.utc)  # cierra las sesiones abiertas
    user.reset_password_token = None
    user.reset_password_token_expiry = None
    db.commit()
    login_limiter.reset(user.email.lower())
    return {"message": "Contraseña actualizada con éxito."}
