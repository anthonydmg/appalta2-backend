from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

SECRET_KEY = settings.jwt_secret_key.get_secret_value()
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days
ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

# Hash de referencia para comparar cuando el usuario no existe: el login tarda lo mismo
# exista o no el correo, así el tiempo de respuesta no revela qué cuentas hay.
_DUMMY_HASH = pwd_context.hash("appalta2-dummy-password")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        pwd_context.verify(plain, _DUMMY_HASH)
        return False
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, token_type: str, expires_in: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**data, "type": token_type, "iat": int(now.timestamp()), "exp": now + expires_in}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict) -> str:
    return _create_token(data, ACCESS, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(data: dict) -> str:
    return _create_token(data, REFRESH, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def issued_before(payload: dict, moment: datetime | None) -> bool:
    """True si el token se emitió antes de `moment` (p. ej. un cambio de contraseña)."""
    if moment is None:
        return False
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return payload.get("iat", 0) < int(moment.timestamp())


def decode_token(token: str, expected_type: str) -> dict | None:
    """Claims de un token válido, vigente y del tipo esperado; None si no lo es.

    Los tokens emitidos antes de agregar el claim "type" se aceptan para ambos usos
    hasta que expiren (máximo REFRESH_TOKEN_EXPIRE_DAYS), así nadie pierde la sesión al desplegar.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if not payload.get("sub") or payload.get("type", expected_type) != expected_type:
        return None
    return payload

def decode_subject(token: str, expected_type: str = ACCESS) -> str | None:
    """Email (claim "sub") de un token válido del tipo esperado; None si no lo es."""
    payload = decode_token(token, expected_type)
    return payload["sub"] if payload else None

def verify_token(token: str = Depends(oauth2_scheme)):
    email = decode_token(token)
    if email is None:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    return email
        

