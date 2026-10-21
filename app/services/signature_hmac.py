"""Firma HMAC-SHA256 de los datos que envían las estaciones.

El mensaje firmado es `station_code|timestamp|battery|sensor1|valor1|sensor2|valor2...`,
con los números sin ceros a la derecha ("NA" si faltan). Debe coincidir byte a byte
con lo que calcula el firmware de la estación.
"""

import hashlib
import hmac
from decimal import Decimal

from app.schemas.station_measurement import StationMeasurementRequest


def normalize_empty(value) -> str:
    if value is None:
        return "NA"
    s = format(Decimal(str(value)), "f").rstrip("0")
    return s + "0" if s.endswith(".") else s


def build_message(station_code: str, data: StationMeasurementRequest) -> str:
    parts = [station_code, str(data.timestamp), normalize_empty(data.battery_level)]
    for measurement in data.measurements:
        parts += [measurement.sensor_code, normalize_empty(measurement.value)]
    return "|".join(parts).strip()


def verify_signature(message: str, secret_key: str, received_signature: str) -> bool:
    expected = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_signature)