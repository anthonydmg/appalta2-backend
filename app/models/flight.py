
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Flight(Base):
    __tablename__ = "flights"

    __table_args__ = (
        CheckConstraint(
            "status IN ('REGISTERED', 'PROCESSING', 'COMPLETED', 'ERROR')",
            name="chk_flights_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    flight_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    field_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    flight_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="REGISTERED",
        server_default="REGISTERED",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    layers = relationship(
        "FlightLayer",
        back_populates="flight",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
