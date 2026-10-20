import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.config import BACKEND_URL, TEMPLATES_DIR
from app.database import user as user_db
from app.database.connection import get_db
from app.schemas import user as user_schemas
from app.services import auth
from app.services.email import send_password_reset_email_gmail, send_verification_email_gmail

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

RESET_TOKEN_TTL = timedelta(hours=1)


def _verification_link(token: str) -> str:
    return f"{BACKEND_URL}/v1/user/verify/{token}"


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

    # El correo se envía tras responder: un SMTP lento o caído no deja al usuario creado
    # con un error 500 (puede pedir el reenvío desde la app).
    background.add_task(send_verification_email_gmail, user.email, _verification_link(verification_token))
    return db_user


@router.post("/user/login", response_model=user_schemas.Token)
def login(user: user_schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = user_db.autenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Correo no verificado")
    return _issue_tokens(db_user)


@router.post("/user/refresh", response_model=user_schemas.Token)
def refresh_token(refresh_token: str = Body(...), db: Session = Depends(get_db)):
    email = auth.decode_subject(refresh_token)
    if email is None:
        raise HTTPException(status_code=401, detail="Token invalido")
    db_user = user_db.get_user_by_email(db, email)
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
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
async def resend_verification(req: user_schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    user = user_db.get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Este correo ya ha sido verificado")

    user.verification_token = str(uuid.uuid4())
    db.commit()

    await send_verification_email_gmail(user.email, _verification_link(user.verification_token))
    return {"message": "Se ha reenviado el correo de verificación. Revisa tu bandeja de entrada."}


@router.post("/user/password/forgot")
async def forgot_password(req: user_schemas.ResetRequest, db: Session = Depends(get_db)):
    user = user_db.get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.reset_password_token = str(uuid.uuid4())
    user.reset_password_token_expiry = datetime.now(timezone.utc) + RESET_TOKEN_TTL
    db.commit()

    await send_password_reset_email_gmail(user.email, f"{BACKEND_URL}/v1/user/reset/{user.reset_password_token}")
    return {"message": "Se ha enviado un enlace de recuperación a tu correo."}


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
    user.reset_password_token = None
    user.reset_password_token_expiry = None
    db.commit()
    return {"message": "Contraseña actualizada con éxito."}
