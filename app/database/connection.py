from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config.config import DATABASE_URL as RAW_DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_SIZE

if not RAW_DATABASE_URL:
    raise ValueError("❌ DATABASE_URL no está definida. Asegúrate de tener un archivo .env")

# Render entrega "postgres://"; SQLAlchemy necesita "postgresql+psycopg2://"
DATABASE_URL = (
    RAW_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    if RAW_DATABASE_URL.startswith("postgres://")
    else RAW_DATABASE_URL
)

engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # descarta conexiones cortadas por el servidor o el proxy
    pool_recycle=1800,
    connect_args={"application_name": "appalta2-api"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
