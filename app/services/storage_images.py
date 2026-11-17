import hashlib

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image as PILImage, UnidentifiedImageError

from app.config.environment import (
    STORAGE_BASE_PATH
)

import os


class InvalidImageError(ValueError):
    pass

class StorageService:
    ALLOWED_FORMATS = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
    }

    def __init__(self):
        self.base_path = Path(STORAGE_BASE_PATH).expanduser().resolve()
        self.optimized_path = self.base_path / "optimized"
        self.original_path = self.base_path / "original"
        self.optimized_path.mkdir(parents=True, exist_ok=True)
        self.original_path.mkdir(parents=True, exist_ok=True)

    def inspect_image(self, content: bytes) -> dict:
        try:
            from io import BytesIO
            with PILImage.open(BytesIO(content)) as img:
                image_format = img.format
                width, height = img.size
                img.verify()
            if image_format not in self.ALLOWED_FORMATS:
                raise InvalidImageError("Formato no permitido. Usa JPG, PNG o WEBP.")
            if width <= 0 or height <= 0:
                raise InvalidImageError("Dimensiones de imagen inválidas.")
            return {
                "format": image_format,
                "extension": self.ALLOWED_FORMATS[image_format],
                "width": width,
                "height": height,
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidImageError("El archivo enviado no es una imagen válida.") from exc

    def save_optimized(self, image_uuid, content: bytes) -> dict:
        info = self.inspect_image(content)
        filename = f"{image_uuid}{info['extension']}"
        destination = self.optimized_path / filename
        print("destination:", destination)
        storage_key = f"optimized/{filename}"

        # Escritura temporal y reemplazo atómico dentro del mismo volumen.
        temp_path = self.optimized_path / f".{uuid4().hex}.tmp"
        try:
            with open(temp_path, "xb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # No sobrescribir archivos existentes: protege reintentos concurrentes.
            if destination.exists():
                raise FileExistsError("Ya existe un archivo para esta imagen.")
            os.replace(temp_path, destination)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

        return {**info, "storage_key": storage_key}

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists() and path.is_file():
            path.unlink()

    def _resolve(self, storage_key: str) -> Path:
        candidate = (self.base_path / storage_key).resolve()
        print("candidate:", candidate)
        if candidate != self.base_path and self.base_path not in candidate.parents:
            raise ValueError("Ruta de almacenamiento inválida.")
        return candidate