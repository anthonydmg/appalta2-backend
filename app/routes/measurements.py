import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from app.config.config import MAX_DRIFT_SECONDS
from app.database.connection import get_db
from app.database.sensor_measurement import get_sensor_history
from app.database.station import get_station_by_station_code
from app.database.station_measurement import UnknownSensorError, save_measurement
from app.schemas.sensor_measurement import SensorMeasurementHistoryItem, SensorMeasurementHistoryResponse
from app.schemas.station_measurement import SensorMeasurementEvent, StationMeasurementEvent, StationMeasurementRequest
from app.services.signature import build_message, verify_signature
from app.services.sse_manager import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter()

StationCode = Path(pattern=r"^[A-Z0-9_-]+$", max_length=50)


def _ingest(db: Session, station_code: str, data: StationMeasurementRequest, signature: str) -> None:
    """Valida firma y anti-replay y guarda la medición (bloqueante: corre en el threadpool)."""
    station = get_station_by_station_code(db, station_code)
    if station is None:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    if abs(int(time.time()) - data.timestamp) > MAX_DRIFT_SECONDS:
        raise HTTPException(status_code=401, detail="Timestamp inválido o expirado")

    if not verify_signature(build_message(station_code, data), station.secret_key, signature):
        logger.warning("Firma inválida de la estación %s", station_code)
        raise HTTPException(status_code=401, detail="Firma inválida")

    if station.last_timestamp is not None and data.timestamp <= station.last_timestamp:
        raise HTTPException(status_code=401, detail="Timestamp repetido")

    try:
        save_measurement(db, station, data)
    except UnknownSensorError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stations/{station_code}/measurements")
async def receive_data(
    data: StationMeasurementRequest,
    station_code: str = StationCode,
    signature: str = Header(..., alias="Signature"),
    db: Session = Depends(get_db),
):
    # La BD es síncrona: se usa el threadpool para no bloquear el event loop (SSE, chat).
    await run_in_threadpool(_ingest, db, station_code, data, signature)

    event = StationMeasurementEvent(
        station_code=station_code,
        timestamp=data.timestamp,
        latitude=data.latitude,
        longitude=data.longitude,
        battery_level=data.battery_level,
        measurements=[SensorMeasurementEvent(sensor_code=m.sensor_code, value=m.value) for m in data.measurements],
    )
    try:
        await sse_manager.broadcast(station_code, event.model_dump())
    except Exception:
        logger.exception("No fue posible enviar el evento SSE para la estación %s", station_code)

    return {"status": "received", "station_id": station_code}


@router.get("/stations/stream")
async def station_stream(station: Optional[str] = Query(None), stations: Optional[str] = Query(None)):
    if station:
        subscriptions = {station}
    elif stations:
        subscriptions = {s.strip() for s in stations.split(",") if s.strip()}
    else:
        subscriptions = None

    queue = await sse_manager.connect(subscriptions)

    async def event_generator():
        try:
            while True:
                yield {"event": "measurement", "data": await queue.get()}
        finally:
            sse_manager.disconnect(queue)

    return EventSourceResponse(event_generator())


@router.get(
    "/stations/{station_code}/sensors/{sensor_code}/measurements",
    response_model=SensorMeasurementHistoryResponse,
)
def sensor_history(
    station_code: str = Path(...),
    sensor_code: str = Path(...),
    start_time: Optional[int] = Query(None),
    end_time: Optional[int] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time debe ser menor o igual que end_time.")

    rows = get_sensor_history(db, station_code, sensor_code, start_time, end_time, limit)
    return SensorMeasurementHistoryResponse(
        station_code=station_code,
        sensor_code=sensor_code,
        measurements=[
            SensorMeasurementHistoryItem(timestamp=row.measurement_timestamp, value=float(row.sensor_value))
            for row in rows
        ],
    )
