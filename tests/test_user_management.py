"""Gestión de usuarios: política de contraseña, correos sin enumeración, límite de intentos y sesiones.

No toca la BD ni el correo: las consultas de usuarios y el envío se reemplazan por dobles en memoria.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from app.database.connection import get_db
from app.routes import user as user_routes
from app.schemas.user import ResetPassword, UserCreate, UserLogin
from app.services import auth
from app.services.rate_limit import RateLimiter, email_limiter, login_limiter

PASSWORD = "Clave#2026"


class FakeUser:
    def __init__(self, email="agricultor@test.pe", verified=True, password=PASSWORD):
        self.id = 1
        self.email = email
        self.firstname, self.father_lastname, self.mother_lastname = "Juan", "Pérez", "Quispe"
        self.hashed_password = auth.hash_password(password)
        self.is_verified = verified
        self.verification_token = None
        self.reset_password_token = None
        self.reset_password_token_expiry = None
        self.password_changed_at = None


class FakeSession:
    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture(autouse=True)
def clean_limiters():
    for limiter in (login_limiter, email_limiter):
        limiter._hits.clear()
    yield


@pytest.fixture
def user():
    return FakeUser()


@pytest.fixture
def sent(monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(to, link):
        sent.append((to, link))

    monkeypatch.setattr(user_routes, "send_verification_email_gmail", fake_send)
    monkeypatch.setattr(user_routes, "send_password_reset_email_gmail", fake_send)
    return sent


@pytest.fixture
def client(monkeypatch, user, sent):
    by_email = lambda db, e: user if e.strip().lower() == user.email.lower() else None
    monkeypatch.setattr(user_routes.user_db, "get_user_by_email", by_email)
    monkeypatch.setattr(
        user_routes.user_db, "autenticate_user",
        lambda db, e, p: user if by_email(db, e) and auth.verify_password(p, user.hashed_password) else None,
    )  # fmt: skip
    monkeypatch.setattr(
        user_routes.user_db, "get_user_by_reset_password_token",
        lambda db, t: user if t and t == user.reset_password_token else None,
    )  # fmt: skip
    app = FastAPI()
    app.include_router(user_routes.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: FakeSession()
    with TestClient(app) as c:
        yield c


# --- Política de contraseña y correo ---------------------------------------------------------

VALID = {
    "email": "Agricultor@Test.PE ",
    "password": PASSWORD,
    "firstname": "Juan",
    "father_lastname": "Pérez",
    "mother_lastname": "Quispe",
    "document_of_identity": "12345678",
    "cellphone": "987654321",
}


@pytest.mark.parametrize("password", ["Ab1#", "abcdefg1#", "ABCDEFG1#", "Abcdefgh#", "Abcdefgh1", "A1#" + "a" * 70])
def test_weak_passwords_are_rejected(password):
    with pytest.raises(ValidationError):
        UserCreate(**{**VALID, "password": password})
    with pytest.raises(ValidationError):
        ResetPassword(token="t", new_password=password)


def test_strong_password_and_normalized_email():
    assert UserCreate(**VALID).email == "agricultor@test.pe"
    assert UserLogin(email=" JUAN@Mail.com", password="x").email == "juan@mail.com"


# --- Sin enumeración de cuentas -------------------------------------------------------------


def test_forgot_password_answers_the_same_for_unknown_email(client, user, sent):
    known = client.post("/api/v1/user/password/forgot", json={"email": user.email})
    unknown = client.post("/api/v1/user/password/forgot", json={"email": "nadie@test.pe"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert [to for to, _ in sent] == [user.email]
    assert user.reset_password_token in sent[0][1]


def test_resend_verification_answers_the_same_for_unknown_or_verified(client, user, sent):
    verified = client.post("/api/v1/user/resend-verification", json={"email": user.email})
    unknown = client.post("/api/v1/user/resend-verification", json={"email": "nadie@test.pe"})
    assert verified.json() == unknown.json() and verified.status_code == 200
    assert sent == []  # ya verificado: no se reenvía

    user.is_verified = False
    client.post("/api/v1/user/resend-verification", json={"email": user.email.upper()})
    assert len(sent) == 1


def test_emails_are_limited_per_address(client, user, sent):
    for _ in range(5):
        assert client.post("/api/v1/user/password/forgot", json={"email": user.email}).status_code == 200
    assert len(sent) == email_limiter.max_attempts


# --- Límite de intentos de login ------------------------------------------------------------


def test_login_is_blocked_after_repeated_failures(client, user):
    login = lambda pwd: client.post("/api/v1/user/login", json={"email": user.email, "password": pwd})
    for _ in range(login_limiter.max_attempts):
        assert login("Incorrecta#1").status_code == 401
    blocked = login(PASSWORD)  # ni la contraseña correcta pasa mientras dure el bloqueo
    assert blocked.status_code == 429
    assert "Demasiados intentos" in blocked.json()["detail"]
    assert int(blocked.headers["Retry-After"]) > 0


def test_successful_login_resets_the_counter(client, user):
    login = lambda pwd: client.post("/api/v1/user/login", json={"email": user.email, "password": pwd})
    for _ in range(login_limiter.max_attempts - 1):
        login("Incorrecta#1")
    assert login(PASSWORD).status_code == 200
    assert login("Incorrecta#1").status_code == 401  # el contador volvió a cero


def test_rate_limiter_window_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now[0])
    limiter = RateLimiter(max_attempts=2, window_seconds=60)
    limiter.hit("a"), limiter.hit("a")
    assert limiter.retry_after("a") == 61
    now[0] += 61
    assert limiter.retry_after("a") == 0
    assert "a" not in limiter._hits


# --- Tokens y sesiones ----------------------------------------------------------------------


def test_refresh_rejects_access_tokens(client, user):
    access = auth.create_access_token({"sub": user.email})
    assert client.post("/api/v1/user/refresh", json=access).status_code == 401
    refresh = auth.create_refresh_token({"sub": user.email})
    assert client.post("/api/v1/user/refresh", json=refresh).status_code == 200


def test_refresh_token_cannot_be_used_as_access_token():
    refresh = auth.create_refresh_token({"sub": "a@b.pe"})
    assert auth.decode_subject(refresh, auth.ACCESS) is None
    assert auth.decode_subject(auth.create_access_token({"sub": "a@b.pe"})) == "a@b.pe"


def test_legacy_tokens_without_type_still_work():
    legacy = jwt.encode(
        {"sub": "a@b.pe", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        auth.SECRET_KEY, algorithm=auth.ALGORITHM,
    )  # fmt: skip
    assert auth.decode_subject(legacy, auth.ACCESS) == auth.decode_subject(legacy, auth.REFRESH) == "a@b.pe"


def test_password_reset_closes_open_sessions(client, user):
    old_refresh = auth.create_refresh_token({"sub": user.email})
    user.reset_password_token = "tok"
    user.reset_password_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    user.password_changed_at = None

    # El reset ocurre después de emitir el token (iat tiene resolución de segundos)
    resp = client.post("/api/v1/user/password/reset", json={"token": "tok", "new_password": "Nueva#Clave9"})
    assert resp.status_code == 200
    user.password_changed_at += timedelta(seconds=1)

    assert client.post("/api/v1/user/refresh", json=old_refresh).status_code == 401
    assert auth.verify_password("Nueva#Clave9", user.hashed_password)
    assert user.reset_password_token is None
    assert client.post("/api/v1/user/login", json={"email": user.email, "password": "Nueva#Clave9"}).status_code == 200


def test_reset_rejects_weak_password_with_readable_message(client, user):
    user.reset_password_token = "tok"
    user.reset_password_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    resp = client.post("/api/v1/user/password/reset", json={"token": "tok", "new_password": "corta"})
    assert resp.status_code == 422
    assert "al menos 8 caracteres" in resp.text


def test_unknown_user_login_takes_a_real_hash_comparison(monkeypatch):
    calls = []
    monkeypatch.setattr(auth.pwd_context, "verify", lambda p, h: calls.append(h) or False)
    assert auth.verify_password("x", None) is False
    assert calls == [auth._DUMMY_HASH]
