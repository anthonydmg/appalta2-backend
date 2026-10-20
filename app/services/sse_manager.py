import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Eventos pendientes por cliente. Si un cliente lento acumula más, se descartan
# sus eventos nuevos en lugar de crecer la memoria del proceso sin límite.
MAX_QUEUE_SIZE = 100


@dataclass(eq=False)
class _Client:
    queue: asyncio.Queue
    stations: set[str] | None  # None = todas las estaciones


class SSEManager:
    """Difunde mediciones a los clientes conectados por Server-Sent Events.

    Vive en memoria del proceso: con varios workers o réplicas cada uno tendría sus
    propios clientes, y habría que publicar los eventos por Redis Pub/Sub o similar.
    """

    def __init__(self):
        self._clients: dict[asyncio.Queue, _Client] = {}

    async def connect(self, stations: set[str] | None = None) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self._clients[queue] = _Client(queue, stations)
        logger.info("Cliente SSE conectado (total=%d, estaciones=%s)", len(self._clients), stations or "todas")
        return queue

    def disconnect(self, queue: asyncio.Queue) -> None:
        self._clients.pop(queue, None)
        logger.info("Cliente SSE desconectado (total=%d)", len(self._clients))

    async def broadcast(self, station_code: str, data) -> None:
        for client in list(self._clients.values()):
            if client.stations is not None and station_code not in client.stations:
                continue
            try:
                client.queue.put_nowait(data)
            except asyncio.QueueFull:
                logger.warning("Cliente SSE saturado: se descarta un evento de %s", station_code)


sse_manager = SSEManager()
