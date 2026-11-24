
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.titiler import get_cog_tilejson, get_cog_info
from app.services.rustfs import (
    object_exists,
    get_file_content
)

import json
import math


router = APIRouter(
    prefix="/maps",
    tags=["Maps"]
)



def calculate_ndvi_summary(flight_id: str, geojson: dict) -> dict:
    features = geojson.get("features", [])

    if not isinstance(features, list):
        raise ValueError("El campo features no contiene una lista válida")

    values = []

    for feature in features:
        properties = feature.get("properties", {})

        if not isinstance(properties, dict):
            continue

        value = properties.get("avg_ndvi")

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        # Ignorar valores no numéricos o fuera del rango NDVI
        if not math.isfinite(value) or not 0 <= value <= 1:
            continue

        values.append(value)

    total_trees = len(features)
    valid_ndvi_count = len(values)
    excluded_trees = total_trees - valid_ndvi_count

    # Clasificación NDVI
    optimal = sum(value > 0.75 for value in values)

    moderate = sum(
        0.55 < value <= 0.75
        for value in values
    )

    low = sum(value <= 0.55 for value in values)

    def category(count: int) -> dict:
        return {
            "count": count,
            "percentage": round(
                count / valid_ndvi_count * 100, 2
            ) if valid_ndvi_count else 0.0
        }

    return {
        "flight_id": flight_id,

        "total_trees": total_trees,
        "valid_ndvi_count": valid_ndvi_count,
        "excluded_trees": excluded_trees,

        "ndvi_statistics": {
            "mean": round(sum(values) / valid_ndvi_count, 4)
            if valid_ndvi_count else None,

            "min": round(min(values), 4)
            if valid_ndvi_count else None,

            "max": round(max(values), 4)
            if valid_ndvi_count else None
        },

        "distribution": {
            "optimal": category(optimal),
            "moderate": category(moderate),
            "low": category(low)
        }
    }

@router.get("/flights/{flight_id}/trees/ndvi/summary")
def get_trees_ndvi_summary(flight_id: str):

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

        # Convertir el contenido del objeto a JSON
        if isinstance(geojson_content, bytes):
            geojson_content = geojson_content.decode("utf-8")

        geojson = json.loads(geojson_content)

        if not isinstance(geojson, dict):
            raise ValueError("El GeoJSON no tiene una estructura válida")

        if geojson.get("type") != "FeatureCollection":
            raise ValueError("El archivo no es un FeatureCollection")

        return calculate_ndvi_summary(
            flight_id=flight_id,
            geojson=geojson
        )

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando GeoJSON: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando resumen NDVI: {str(e)}"
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
