from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class CropField(Base):
    __tablename__ = "crop_fields"

    id = Column(BigInteger, primary_key=True, index=True)

    field_code = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)

    crop_common_name = Column(
        String(50),
        nullable=False,
        default="Palto",
        server_default="Palto",
    )
    crop_scientific_name = Column(
        String(100),
        nullable=False,
        default="Persea americana",
        server_default="Persea americana",
    )
    crop_variety = Column(
        String(50),
        nullable=False,
        default="Hass",
        server_default="Hass",
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

    field_mappings = relationship(
        "FieldMapping",
        back_populates="crop_field",
    )

    department = Column(String(100), nullable=False)
    province = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)