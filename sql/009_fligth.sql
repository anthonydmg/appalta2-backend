
CREATE TABLE flights (
    id BIGSERIAL PRIMARY KEY,

    flight_code VARCHAR(100) NOT NULL UNIQUE,

    field_name VARCHAR(200) NOT NULL,

    flight_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'REGISTERED'
        CHECK (
            status IN (
                'REGISTERED',
                'PROCESSING',
                'COMPLETED',
                'ERROR'
            )
        ),

    description TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE flight_layers (
    id BIGSERIAL PRIMARY KEY,

    flight_id BIGINT NOT NULL,

    layer_type VARCHAR(30) NOT NULL
        CHECK (
            layer_type IN (
                'RGB',
                'NDVI',
                'NDRE',
                'NDWI',
                'TREES',
                'PLOTS'
            )
        ),

    storage_bucket VARCHAR(100) NOT NULL,

    object_key TEXT NOT NULL,

    content_type VARCHAR(100) NOT NULL,

    file_size_bytes BIGINT,

    crs_epsg INTEGER,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_flight_layers_flight
        FOREIGN KEY (flight_id)
        REFERENCES flights(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_flight_layer_type
        UNIQUE (flight_id, layer_type),

    CONSTRAINT uq_storage_object
        UNIQUE (storage_bucket, object_key),

    CONSTRAINT chk_file_size
        CHECK (
            file_size_bytes IS NULL
            OR file_size_bytes >= 0
        )
);


CREATE INDEX idx_flights_flight_date
    ON flights(flight_date);

CREATE INDEX idx_flight_layers_flight_id
    ON flight_layers(flight_id);

CREATE INDEX idx_flight_layers_type
    ON flight_layers(layer_type);
