from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    DateTime
)

from app.database.connection import Base


class LeafCondition(Base):
    __tablename__ = "leaf_conditions"

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    id_class_model = Column(
        Integer,
        unique=True,
        nullable=False
    )

    name = Column(
        String(200),
        nullable=False
    )

    side_leaf = Column(
        String(10),
        nullable=False
    )

    pest_taxonomy = Column(
        String(255),
        nullable=True
    )

    description = Column(Text, nullable=True)

    title_recommendation_1 = Column(
        String(255),
        nullable=True
    )
    recommendation_1 = Column(Text, nullable=True)

    title_recommendation_2 = Column(
        String(255),
        nullable=True
    )
    recommendation_2 = Column(Text, nullable=True)

    title_recommendation_3 = Column(
        String(255),
        nullable=True
    )
    recommendation_3 = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False
    )
