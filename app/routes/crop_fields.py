from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.crop_field import CropField
from app.models.field_mapping import FieldMapping
from app.schemas.crop_field import CropFieldCreate, CropFieldOverviewResponse, CropFieldResponse, LatestFieldMappingResponse


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


@router.get(
    "/overview",
    response_model=list[CropFieldOverviewResponse],
)
def get_crop_fields_overview(
    db: Session = Depends(get_db),
):
    # Numera los vuelos de cada parcela, del más reciente al más antiguo.
    latest_mapping = (
        select(
            FieldMapping.id.label("id"),
            FieldMapping.field_id.label("field_id"),
            FieldMapping.field_mapping_id.label("field_mapping_id"),
            FieldMapping.field_mapping_name.label("field_mapping_name"),
            FieldMapping.flight_date.label("flight_date"),
            FieldMapping.status.label("status"),
            func.row_number()
            .over(
                partition_by=FieldMapping.field_id,
                order_by=(
                    FieldMapping.flight_date.desc(),
                    FieldMapping.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .subquery()
    )

    rows = db.execute(
        select(
            CropField,
            latest_mapping.c.id,
            latest_mapping.c.field_mapping_id,
            latest_mapping.c.field_mapping_name,
            latest_mapping.c.flight_date,
            latest_mapping.c.status,
        )
        .outerjoin(
            latest_mapping,
            (latest_mapping.c.field_id == CropField.id)
            & (latest_mapping.c.row_number == 1),
        )
        .order_by(CropField.name.asc())
    ).all()

    result = []

    for row in rows:
        crop_field = row[0]

        mapping = None
        if row.id is not None:
            mapping = LatestFieldMappingResponse(
                id=row.id,
                field_mapping_id=row.field_mapping_id,
                field_mapping_name=row.field_mapping_name,
                flight_date=row.flight_date,
                status=row.status,
            )

        result.append(
            CropFieldOverviewResponse(
                id=crop_field.id,
                field_code=crop_field.field_code,
                name=crop_field.name,
                department=crop_field.department,
                province=crop_field.province,
                district=crop_field.district,
                latest_field_mapping=mapping,
            )
        )

    return result