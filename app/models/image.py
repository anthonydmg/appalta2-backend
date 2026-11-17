from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Integer,
    Float,
    String,
    text
)
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    client_uuid = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False
    )

    optimized_storage_path = Column(
        Text,
        unique=True,
        nullable=False
    )

    original_storage_path = Column(
        Text,
        unique=True,
        nullable=True
    )

    optimized_size = Column(
        BigInteger,
        nullable=False
    )

    optimized_width = Column(Integer, nullable=True)
    optimized_height = Column(Integer, nullable=True)

    original_size = Column(BigInteger, nullable=True)
    original_width = Column(Integer, nullable=True)
    original_height = Column(Integer, nullable=True)

    optimized_uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

    original_uploaded_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    optimized_status = Column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )
    original_status = Column(
        String(20), nullable=False, server_default=text("'NOT_UPLOADED'")
    )

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    captured_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

    received_at = Column(
        DateTime(timezone=True),
        nullable=False
    )


