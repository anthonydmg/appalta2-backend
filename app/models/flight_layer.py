
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FlightLayer(Base):
    __tablename__ = "flight_layers"

    __table_args__ = (
        CheckConstraint(
            "layer_type IN ('RGB', 'NDVI', 'NDRE', 'NDWI', 'TREES', 'PLOTS')",
            name="chk_flight_layers_type",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="chk_file_size",
        ),
        UniqueConstraint(
            "flight_id",
            "layer_type",
            name="uq_flight_layer_type",
        ),
        UniqueConstraint(
            "storage_bucket",
            "object_key",
            name="uq_storage_object",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    flight_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("flights.id", ondelete="CASCADE"),
        nullable=False,
    )

    layer_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    object_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    crs_epsg: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # "metadata" es reservado en SQLAlchemy declarativo.
    # Por eso utilizamos metadata_json como atributo Python.
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relación
    flight = relationship(
        "Flight",
        back_populates="layers",
    )
