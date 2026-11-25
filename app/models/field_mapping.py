from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    id = Column(BigInteger, primary_key=True, index=True)

    uuid_local = Column(UUID(as_uuid=True), nullable=False, unique=True)

    field_mapping_id = Column(String(100), nullable=False, unique=True)
    field_mapping_name = Column(String(100), nullable=False)

    flight_date = Column(Date, nullable=False)
    field_id = Column(
        BigInteger,
        ForeignKey("crop_fields.id"),
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="REGISTERED",
        server_default="REGISTERED",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    crop_field = relationship(
        "CropField",
        back_populates="field_mappings",
    )