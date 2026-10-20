from sqlalchemy import BigInteger, Column, DateTime, String, func

from app.database.connection import Base


class Station(Base):
    __tablename__ = "stations"
    id = Column(BigInteger, primary_key=True, index=True)
    station_code = Column(String, unique=True)
    name = Column(String)
    mac_address = Column(String)
    secret_key = Column(String)
    last_timestamp = Column(BigInteger)  # BIGINT en sql/001_schema.sql (último timestamp aceptado, anti-replay)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
