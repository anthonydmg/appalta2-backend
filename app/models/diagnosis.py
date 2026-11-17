from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    DateTime,
    ForeignKey,
    text
)
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"

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

    id_image = Column(
        BigInteger,
        ForeignKey("images.id"),
        unique=True,
        nullable=False
    )

    id_user = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_date = Column(
        DateTime(timezone=True),
        nullable=False
    )

    side_leaf = Column(
        String(10),
        nullable=False
    )

    received_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    sync_status = Column(String(30), nullable=False, server_default=text("'METADATA_SYNCED'"))
