from sqlalchemy import (
    Column,
    BigInteger,
    ForeignKey,
    Numeric,
    UniqueConstraint
)

from app.database.connection import Base


class DetectedLeafCondition(Base):
    __tablename__ = "detected_leaf_conditions"

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

    id_condition = Column(
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
            "id_condition",
            name="uq_detected_leaf_conditions_diagnosis_class"
        ),
    )
