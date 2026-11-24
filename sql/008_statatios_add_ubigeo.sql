
-- =====================================================
-- 1. HABILITAR POSTGIS
-- =====================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- =====================================================
-- 2. CREAR ESQUEMA GEOGRAPHY
-- =====================================================

CREATE SCHEMA IF NOT EXISTS geography;

-- =====================================================
-- 3. CREAR TABLA DE DISTRITOS DEL PERÚ
-- =====================================================

CREATE TABLE IF NOT EXISTS geography.districts (
    id BIGSERIAL PRIMARY KEY,
    ubigeo VARCHAR(6) UNIQUE NOT NULL,
    department VARCHAR(100),
    province VARCHAR(100),
    district VARCHAR(100),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);

-- Índice espacial
CREATE INDEX IF NOT EXISTS idx_districts_geom
ON geography.districts
USING GIST (geom);

-- =====================================================
-- 4. AGREGAR COLUMNAS GEOGRÁFICAS A STATIONS
-- =====================================================

ALTER TABLE stations
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ubigeo VARCHAR(6),
    ADD COLUMN IF NOT EXISTS location GEOMETRY(Point, 4326);

-- Índice espacial de estaciones
CREATE INDEX IF NOT EXISTS idx_stations_location
ON stations
USING GIST (location);


-- =====================================================
-- 5. VERIFICAR ESTRUCTURA
-- =====================================================

SELECT
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'stations'
ORDER BY ordinal_position;

-- Verificar tabla de distritos
SELECT
    COUNT(*) AS total_distritos
FROM geography.districts;