
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TITILER_URL = os.getenv(
    "TITILER_URL",
    "http://localhost:8001"
)


async def get_cog_info(object_key: str):
    """
    Obtiene los metadatos de un COG almacenado en RustFS
    mediante TiTiler.
    """

    bucket = os.getenv("RUSTFS_BUCKET")

    cog_path = f"/vsis3/{bucket}/{object_key}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            f"{TITILER_URL}/cog/info",
            params={"url": cog_path}
        )

        response.raise_for_status()

        return response.json()


async def get_cog_tilejson(object_key: str):
    """
    Obtiene TileJSON para visualizar el COG en MapLibre.
    """

    bucket = os.getenv("RUSTFS_BUCKET")

    cog_path = f"/vsis3/{bucket}/{object_key}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            f"{TITILER_URL}/cog/WebMercatorQuad/tilejson.json",
            params={"url": cog_path}
        )

        response.raise_for_status()

        return response.json()
