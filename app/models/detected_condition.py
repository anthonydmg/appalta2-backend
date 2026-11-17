from sqlalchemy import (
    Column,
    BigInteger,
    ForeignKey,
    Numeric,
    UniqueConstraint
)

from app.database.connection import Base


class DetectedCondition(Base):
    __tablename__ = "detected_conditions"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    id_diagnosis = Column(
        BigInteger,
        ForeignKey(
            "diagnoses.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    id_class = Column(
        BigInteger,
        ForeignKey("leaf_conditions.id"),
        nullable=False
    )

    probability = Column(
        Numeric(7, 6),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "id_diagnosis",
            "id_class",
            name="uq_detected_conditions_diagnosis_class"
        ),
    )
