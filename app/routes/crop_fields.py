from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.crop_field import CropField
from app.models.field_mapping import FieldMapping
from app.schemas.crop_field import CropFieldCreate, CropFieldResponse


router = APIRouter(
    prefix="/crop-fields",
    tags=["Crop Fields"],
)


@router.post(
    "/create",
    response_model=CropFieldResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_crop_field(
    payload: CropFieldCreate,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(CropField.id).where(
            CropField.field_code == payload.field_code
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una parcela con ese código.",
        )

    crop_field = CropField(**payload.model_dump())

    db.add(crop_field)
    db.commit()
    db.refresh(crop_field)

    return crop_field


@router.delete(
    "/{crop_field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_crop_field(
    crop_field_id: int,
    db: Session = Depends(get_db),
):
    crop_field = db.get(CropField, crop_field_id)

    if crop_field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la parcela.",
        )

    mapping_exists = db.scalar(
        select(FieldMapping.id)
        .where(FieldMapping.field_id == crop_field_id)
        .limit(1)
    )

    if mapping_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede eliminar la parcela porque tiene "
                "vuelos de mapeo asociados."
            ),
        )

    db.delete(crop_field)
    db.commit()

    return None