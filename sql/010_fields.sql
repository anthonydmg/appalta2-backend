CREATE TABLE crop_fields (
    id BIGSERIAL PRIMARY KEY,

    field_code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,

    department VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,

    crop_common_name VARCHAR(50) NOT NULL DEFAULT 'Palto',
    crop_scientific_name VARCHAR(100) NOT NULL DEFAULT 'Persea americana',
    crop_variety VARCHAR(50) NOT NULL DEFAULT 'Hass',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE field_mappings (
    id BIGSERIAL PRIMARY KEY,

    uuid_local UUID NOT NULL UNIQUE,

    field_mapping_id VARCHAR(100) NOT NULL UNIQUE,
    field_mapping_name VARCHAR(100) NOT NULL,

    flight_date DATE NOT NULL,
    field_id BIGINT NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'REGISTERED'
        CHECK (
            status IN (
                'REGISTERED',
                'PROCESSING',
                'COMPLETED',
                'ERROR'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_field_mappings_field
        FOREIGN KEY (field_id)
        REFERENCES crop_fields(id)
);

CREATE INDEX idx_field_mappings_field_date
    ON field_mappings(field_id, flight_date DESC);