from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.crop_field import CropField
from app.models.field_mapping import FieldMapping
from app.schemas.field_mapping import (
    FieldMappingCreate,
    FieldMappingResponse,
)


router = APIRouter(
    prefix="/field-mappings",
    tags=["Field Mappings"],
)


@router.post(
    "/create",
    response_model=FieldMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_field_mapping(
    payload: FieldMappingCreate,
    db: Session = Depends(get_db),
):
    # Si el escritorio reintenta con el mismo UUID,
    # devuelve el registro existente y evita duplicarlo.
    existing = db.scalar(
        select(FieldMapping).where(
            FieldMapping.uuid_local == payload.uuid_local
        )
    )

    if existing is not None:
        if existing.field_id != payload.field_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El uuid_local ya está asociado a otra parcela."
                ),
            )

        return existing

    # Verifica que la parcela exista.
    crop_field = db.get(CropField, payload.field_id)

    if crop_field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la parcela indicada en field_id.",
        )

    # Evita reutilizar el identificador de almacenamiento.
    existing_mapping_id = db.scalar(
        select(FieldMapping.id).where(
            FieldMapping.field_mapping_id == payload.field_mapping_id
        )
    )

    if existing_mapping_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un mapeo con ese field_mapping_id.",
        )

    field_mapping = FieldMapping(
        uuid_local=payload.uuid_local,
        field_mapping_id=payload.field_mapping_id,
        field_mapping_name=payload.field_mapping_name,
        flight_date=payload.flight_date,
        field_id=payload.field_id,
        status="REGISTERED",
    )

    db.add(field_mapping)
    db.commit()
    db.refresh(field_mapping)

    return field_mapping