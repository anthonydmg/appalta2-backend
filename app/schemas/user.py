import re

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

DNI_PATTERN = re.compile(r"\d{8}")
CELLPHONE_PATTERN = re.compile(r"\d{9}")
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()-_=+[{]}|;:'\",<.>/?"
BCRYPT_MAX_BYTES = 72  # bcrypt ignora (o rechaza) lo que pase de 72 bytes


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_password_strength(value: str) -> str:
    """Misma política que el formulario de registro de la app."""
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError("La contraseña es demasiado larga")
    if not (
        any(c.islower() for c in value)
        and any(c.isupper() for c in value)
        and any(c.isdigit() for c in value)
        and any(c in PASSWORD_SPECIAL_CHARS for c in value)
    ):
        raise ValueError("La contraseña debe tener mayúsculas, minúsculas, números y un carácter especial")
    return value


class EmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class UserCreate(EmailRequest):
    password: str
    firstname: str
    father_lastname: str
    mother_lastname: str
    document_of_identity: str
    cellphone: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("document_of_identity")
    @classmethod
    def validate_dni(cls, value: str) -> str:
        value = value.strip()
        if not DNI_PATTERN.fullmatch(value):
            raise ValueError("El número de DNI debe tener exactamente 8 dígitos")
        return value

    @field_validator("cellphone")
    @classmethod
    def validate_cellphone(cls, value: str) -> str:
        value = value.strip()
        if not CELLPHONE_PATTERN.fullmatch(value):
            raise ValueError("El número de celular debe tener exactamente 9 dígitos")
        return value


class UserLogin(EmailRequest):
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    firstname: str


class UserInfo(BaseModel):
    firstname: str
    father_lastname: str
    mother_lastname: str
    email: EmailStr

    @classmethod
    def from_user(cls, user) -> "UserInfo":
        return cls(
            firstname=user.firstname,
            father_lastname=user.father_lastname,
            mother_lastname=user.mother_lastname,
            email=user.email,
        )


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_info: UserInfo


class ResendVerificationRequest(EmailRequest):
    pass


class ResetRequest(EmailRequest):
    pass


class ResetPassword(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)
