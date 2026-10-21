from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.services import auth


def get_user_by_email(db: Session, email: str) -> User | None:
    # Sin distinguir mayúsculas: cuentas antiguas pueden estar guardadas con mayúsculas
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def get_user_by_document(db: Session, document_of_identity: str) -> User | None:
    return db.query(User).filter(User.document_of_identity == document_of_identity).first()


def get_user_by_token(db: Session, verification_token: str) -> User | None:
    return db.query(User).filter(User.verification_token == verification_token).first()


def get_user_by_reset_password_token(db: Session, reset_password_token: str) -> User | None:
    return db.query(User).filter(User.reset_password_token == reset_password_token).first()


def create_user(db: Session, user: UserCreate, verification_token: str) -> User:
    db_user = User(
        email=user.email,
        firstname=user.firstname,
        hashed_password=auth.hash_password(user.password),
        father_lastname=user.father_lastname,
        mother_lastname=user.mother_lastname,
        document_of_identity=user.document_of_identity,
        cellphone=user.cellphone,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def autenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    # verify_password compara contra un hash ficticio si el usuario no existe (mismo tiempo de respuesta)
    if not auth.verify_password(password, user.hashed_password if user else None):
        return None
    return user
