
import geopandas as gpd
from sqlalchemy import create_engine
from geoalchemy2 import Geometry

# 1. Leer GeoPackage
gdf = gpd.read_file(
    "./locations/DISTRITO.gpkg",
    layer="DISTRITO"
)

# 2. Revisar columnas disponibles
print(gdf.columns.tolist())
print(gdf.crs)

# 3. Normalizar sistema de coordenadas
gdf = gdf.to_crs(epsg=4326)

# 4. Normalizar geometrías a MultiPolygon
from shapely.geometry import MultiPolygon

gdf.geometry = gdf.geometry.apply(
    lambda geom: (
        MultiPolygon([geom])
        if geom.geom_type == "Polygon"
        else geom
    )
)

# 5. Renombrar geometría
gdf = gdf.rename_geometry("geom")

# 6. Conectar a PostgreSQL
engine = create_engine(
    "postgresql+psycopg://postgres:postgres123@localhost:5432/develop_appalta2"
)
# 7. Importar a PostgreSQL
gdf.to_postgis(
    name="districts",
    con=engine,
    schema="geography",
    if_exists="replace",
    index=False,
    dtype={
        "geom": Geometry("MULTIPOLYGON", srid=4326)
    }
)

print("Importación completada correctamente")
