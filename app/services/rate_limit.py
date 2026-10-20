"""Límite de intentos en memoria del proceso (ventana deslizante por clave).

Suficiente con un solo worker de uvicorn (ver DEPLOY.md); con varios procesos o
réplicas cada uno contaría por su lado y habría que mover los contadores a Redis.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()  # las rutas síncronas corren en el threadpool

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if not hits:
            del self._hits[key]  # no acumular claves de correos que ya no intentan
            return deque()
        return hits

    def retry_after(self, key: str) -> int:
        """Segundos hasta poder intentar de nuevo; 0 si no está bloqueado."""
        with self._lock:
            now = time.monotonic()
            hits = self._prune(key, now)
            if len(hits) < self.max_attempts:
                return 0
            return int(self.window - (now - hits[0])) + 1

    def hit(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


# 5 contraseñas incorrectas por correo cada 15 minutos
login_limiter = RateLimiter(max_attempts=5, window_seconds=15 * 60)
# 3 correos (verificación o recuperación) por dirección cada 15 minutos: evita usar el API para spam
email_limiter = RateLimiter(max_attempts=3, window_seconds=15 * 60)
