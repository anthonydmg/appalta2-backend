from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import station as station_db
from app.database.connection import get_db
from app.database.sensor_measurement import get_sensors_by_measurement
from app.database.station_measurement import get_latest_station_measurement
from app.schemas.station import StationResponse

router = APIRouter()


@router.get("/stations", response_model=list[StationResponse])
def get_all_stations(db: Session = Depends(get_db)):
    return station_db.get_all_stations(db)


@router.get("/stations/{station_code}/latest", response_model=StationResponse)
def get_latest_station(station_code: str = Path(...), db: Session = Depends(get_db)):
    result = get_latest_station_measurement(db, station_code)
    if result is None:
        raise HTTPException(status_code=404, detail="Estación no encontrada.")

    station, measurement = result
    sensors = get_sensors_by_measurement(db, [measurement.id]).get(measurement.id, []) if measurement else []
    return StationResponse.from_orm_rows(station, measurement, sensors)
