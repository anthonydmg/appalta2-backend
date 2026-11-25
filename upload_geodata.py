
from pathlib import Path

from app.services.rustfs import (
    upload_file,
    object_exists,
    test_rustfs_connection
)

# Directorio donde están tus archivos
DATA_DIR = Path(r"C:\Users\Anthony\Local\paltas_proyecto\vuelos\analysis\noviembre-2026-david-anticona")

# Organización dentro de RustFS
BASE_KEY = "flights/noviembre-2026-david-anticona"

# Archivos locales
raster_path = DATA_DIR / "mosaic" / "rgb" / "rgb_cog.tif"
geojson_path = DATA_DIR / "mosaic" / "trees_ndvi.geojson"

# 1. Verificar conexión
print(test_rustfs_connection())

# 2. Subir mosaico COG
raster_key = f"{BASE_KEY}/raster/rgb_cog.tif"

if not object_exists(raster_key):
    print("Subiendo mosaico COG...")

    print(upload_file(
        local_path=str(raster_path),
        object_key=raster_key,
        content_type="image/tiff"
    ))
else:
    print("El mosaico ya existe en RustFS")

# 3. Subir polígonos GeoJSON
geojson_key = f"{BASE_KEY}/vectors/trees_ndvi.geojson"

if not object_exists(geojson_key):
    print("Subiendo polígonos GeoJSON...")

    print(upload_file(
        local_path=str(geojson_path),
        object_key=geojson_key,
        content_type="application/geo+json"
    ))
else:
    print("El GeoJSON ya existe en RustFS")

print("Proceso finalizado")
