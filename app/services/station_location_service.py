
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def update_station_location(
    db: Session,
    station_id: int,
    latitude: float | None,
    longitude: float | None
) -> bool:
    """
    Actualiza la última ubicación conocida de una estación
    y determina su UBIGEO mediante PostGIS.

    Retorna True si encontró un distrito y actualizó la estación.
    """

    # Validar coordenadas
    if latitude is None or longitude is None:
        return False

    if latitude == 0 or longitude == 0:
        return False

    if not (-90 <= latitude <= 90):
        return False

    if not (-180 <= longitude <= 180):
        return False

    query = text("""
        UPDATE stations s
        SET
            latitude = :latitude,
            longitude = :longitude,
            ubigeo = d.ubigeo,
            location = ST_SetSRID(
                ST_MakePoint(
                    :longitude,
                    :latitude
                ),
                4326
            )
        FROM geography.districts d
        WHERE s.id = :station_id
          AND ST_Covers(
              d.geom,
              ST_SetSRID(
                  ST_MakePoint(
                      :longitude,
                      :latitude
                  ),
                  4326
              )
          )
        RETURNING
            s.station_code,
            s.ubigeo;
    """)

    try:
        # Savepoint para aislar posibles errores de esta actualización
        with db.begin_nested():
            result = db.execute(
                query,
                {
                    "station_id": station_id,
                    "latitude": latitude,
                    "longitude": longitude
                }
            )

            row = result.fetchone()

        if row is None:
            logger.warning(
                "No se encontró distrito para station_id=%s "
                "con coordenadas (%s, %s)",
                station_id,
                latitude,
                longitude
            )
            return False

        logger.info(
            "Ubicación actualizada: estación=%s, UBIGEO=%s",
            row.station_code,
            row.ubigeo
        )

        return True

    except Exception:
        logger.exception(
            "Error actualizando ubicación de station_id=%s",
            station_id
        )
        return False
