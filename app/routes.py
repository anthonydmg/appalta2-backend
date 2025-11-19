from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from . import crud, schemas, auth
from .database import get_db
from jose import jwt, JWTError
import uuid
from app.config import BACKEND_URL
from app.utils import send_verification_email, send_password_reset_email
import datetime
from datetime import datetime, timedelta, timezone

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/register", response_model = schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail = "Email ya registrado")
    
    verification_token = str(uuid.uuid4())
    
    db_user = crud.create_user(db, user, verification_token)

    verification_link = f"{BACKEND_URL}/api/verify/{verification_token}"
    await send_verification_email(user.email, verification_link)
    return db_user


@router.post("/login", response_model = schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    print("user:", user)
    db_user = crud.autenticate_user(db, user.email, user.password)
    print("db_user:", db_user)
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    

    if not db_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Correo no verificado"
        )

    access_token = auth.create_access_token({
        "sub": db_user.email
    })

    refresh_token = auth.create_refresh_token({
        "sub": db_user.email
    })

    user_info = schemas.UserInfo(
        firstname = db_user.firstname,
        father_lastname =db_user.father_lastname,
        mother_lastname = db_user.mother_lastname,
        email=db_user.email
    )

    resp = schemas.Token(access_token=access_token, refresh_token=refresh_token, user_info=user_info)
    print("resp:", resp)
    return resp

@router.post("/refresh", response_model = schemas.Token)
def refresh_token(refresh_token: str = Body(...), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
    
    db_user = crud.get_user_by_email(db, email)

    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    new_access = auth.create_access_token({"sub": db_user.email})
    new_refresh = auth.create_refresh_token({"sub": db_user.email})
    
    user_info = schemas.UserInfo(
        firstname = db_user.firstname,
        father_lastname =db_user.father_lastname,
        mother_lastname = db_user.mother_lastname,
        email=db_user.email
    )

    return schemas.Token(access_token=new_access, refresh_token=new_refresh, user_info=user_info)


@router.get("/me", response_model=schemas.UserResponse)
def get_me(email: str = Depends(auth.verify_token), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("/verify/{token}")
def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=404, detail="Token inválido")
    
    user.is_verified = True
    user.verification_token = None
    db.commit()

    return templates.TemplateResponse("verified.html", {"request": request})

@router.post("/resend-verification")
async def resend_verification(req: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    print("req.email:", req.email)
    user = crud.get_user_by_email(db, req.email)
    print("user:", user)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Este correo ya ha sido verificado")
    

    # Generar nuevo token y fecha de expiración
    new_token = str(uuid.uuid4())

    user.verification_token = new_token
    
    db.commit()

    # Generar el nuevo enlace
    verification_link = f"{BACKEND_URL}/api/verify/{new_token}"

    # Enviar el correo de verificación
    await send_verification_email(user.email, verification_link)

    return {"message": "Se ha reenviado el correo de verificación. Revisa tu bandeja de entrada."}  

@router.post("/password/forgot")
async def forgot_password(req: schemas.ResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # generar token y expiración
    user.reset_password_token = str(uuid.uuid4())
    user.reset_password_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    # enviar correo con enlace
    link = f"{BACKEND_URL}/api/reset/{user.reset_password_token}"
    await send_password_reset_email(user.email, link)

    return {"message": "Se ha enviado un enlace de recuperación a tu correo."}


@router.get("/reset/{token}", response_class=HTMLResponse)
def serve_reset_page(token: str, request: Request, db: Session = Depends(get_db)):
    user = crud.get_user_by_reset_password_token(db, token)
    
    if not user:
        return templates.TemplateResponse(
            "invalid_link.html", {"request": request}
        )
    
    expiry = user.reset_password_token_expiry
    # Si la fecha es naive, añádele zona horaria UTC
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expiry:
        return templates.TemplateResponse(
            "invalid_link.html", {"request": request}
        )
   
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/password/reset")
def reset_password(req: schemas.ResetPassword, db: Session = Depends(get_db)):
    user = crud.get_user_by_reset_password_token(db, req.token)

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado.")
    
    expiry = user.reset_password_token_expiry
    # Si la fecha es naive, añádele zona horaria UTC
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expiry:
        raise HTTPException(status_code=400, detail="Token inválido o expirado.")
    
    # actualizar contraseña
    user.hashed_password = auth.hash_password(req.new_password)
    user.reset_password_token = None
    user.reset_password_token_expiry = None
    db.commit()

    return {"message": "Contraseña actualizada con éxito."}