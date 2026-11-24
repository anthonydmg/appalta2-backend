
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.titiler import get_cog_tilejson, get_cog_info
from app.services.rustfs import (
    object_exists,
    get_file_content
)

router = APIRouter(
    prefix="/maps",
    tags=["Maps"]
)



@router.get("/flights/{flight_id}/trees/ndvi")
def get_trees_ndvi(flight_id: str):

    object_key = (
        f"flights/{flight_id}/vectors/trees_ndvi.geojson"
    )

    if not object_exists(object_key):
        raise HTTPException(
            status_code=404,
            detail="GeoJSON de árboles no encontrado"
        )

    try:
        geojson_content = get_file_content(object_key)

        return Response(
            content=geojson_content,
            media_type="application/geo+json"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener GeoJSON: {str(e)}"
        )

@router.get("/flights/{flight_id}/rgb/info")
async def get_rgb_info(flight_id: str):

    object_key = (
        f"flights/{flight_id}/raster/rgb_cog.tif"
    )

    try:
        if not object_exists(object_key):
            raise HTTPException(
                status_code=404,
                detail="RGB mosaic not found"
            )

        return await get_cog_info(object_key)

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Error retrieving raster information: {str(error)}"
        )


@router.get("/flights/{flight_id}/rgb/tilejson")
async def get_rgb_tilejson(flight_id: str):

    object_key = (
        f"flights/{flight_id}/raster/rgb_cog.tif"
    )

    try:
        if not object_exists(object_key):
            raise HTTPException(
                status_code=404,
                detail="RGB mosaic not found"
            )

        return await get_cog_tilejson(object_key)

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Error generating TileJSON: {str(error)}"
        )
