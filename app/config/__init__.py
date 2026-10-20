from app.config.environment import Settings, get_settings

__all__ = ["Settings", "get_settings", "settings"]


def __getattr__(name: str):
    # `from app.config import settings` lee el .env al primer uso, no al importar el paquete:
    # así scripts.check_env puede revisar otro archivo aunque el .env local tenga errores.
    if name == "settings":
        return get_settings()
    raise AttributeError(name)
