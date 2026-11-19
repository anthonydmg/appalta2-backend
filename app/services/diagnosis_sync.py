
from decimal import Decimal
import logging

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.image import Image
from app.models.leaf_condition import LeafCondition
from app.models.diagnosis import Diagnosis
from app.models.detected_condition import DetectedLeafCondition

from app.schemas.diagnosis_sync import DiagnosisSyncItem

from app.services.storage_images import StorageService


logger = logging.getLogger(__name__)

storage = StorageService()

class SyncConflictError(Exception):
    pass


class UnknownModelClassError(Exception):
    pass


def _existing_metadata_result(db: Session, item: DiagnosisSyncItem, user_id: int):
    existing = db.query(Diagnosis).filter(
        Diagnosis.client_uuid == item.diagnosis_client_uuid
    ).first()
    if existing is None:
        return None
    if existing.id_user != user_id:
        raise SyncConflictError("El diagnóstico ya existe y pertenece a otro usuario.")

    image = db.query(Image).filter(Image.id == existing.id_image).first()
    if image is None or image.client_uuid != item.image_client_uuid:
        raise SyncConflictError("El UUID de imagen no coincide con el diagnóstico existente.")

    return {
        "diagnosis_client_uuid": item.diagnosis_client_uuid,
        "image_client_uuid": item.image_client_uuid,
        "status": existing.sync_status,
        "image_status": image.optimized_status,
        "id_diagnosis": existing.id,
        "id_image": image.id,
        "message": (
            "El diagnóstico ya estaba completamente sincronizado."
            if existing.sync_status == "SYNCED"
            else "Los metadatos ya están registrados. Falta cargar la imagen optimizada."
        ),
    }

def register_diagnosis_metadata(
    db: Session,
    item: DiagnosisSyncItem,
    user_id: int,
) -> dict:
    """Registra metadatos. La imagen optimizada queda pendiente de carga."""
    try:
        existing_result = _existing_metadata_result(db, item, user_id)
        if existing_result:
            return existing_result

        existing_image = db.query(Image).filter(
            Image.client_uuid == item.image_client_uuid
        ).first()
        if existing_image:
            raise SyncConflictError(
                "La imagen ya está asociada a otro registro o diagnóstico."
            )

        model_class_ids = [s.id_class_model for s in item.detected_leaf_conditions]
        if len(model_class_ids) != len(set(model_class_ids)):
            raise SyncConflictError("El diagnóstico contiene clases repetidas.")

        class_map = {}
        if model_class_ids:
            conditions = db.query(LeafCondition).filter(
                LeafCondition.id_class_model.in_(model_class_ids)
            ).all()
            class_map = {c.id_class_model: c for c in conditions}
            missing = sorted(set(model_class_ids) - set(class_map))
            if missing:
                raise UnknownModelClassError(
                    f"No existen estas clases en leaf_conditions: {missing}"
                )
            wrong_side = [
                class_id for class_id, condition in class_map.items()
                if condition.side_leaf != item.side_leaf
            ]
            if wrong_side:
                raise SyncConflictError(
                    f"Las clases {wrong_side} no corresponden a la cara '{item.side_leaf}'."
                )

        now = datetime.now(timezone.utc)
        image = Image(
            client_uuid=item.image_client_uuid,
            optimized_storage_path=None,
            optimized_size=None,
            optimized_width=None,
            optimized_height=None,
            optimized_uploaded_at=None,
            optimized_status="PENDING",
            original_storage_path=None,
            original_size=None,
            original_width=None,
            original_height=None,
            original_uploaded_at=None,
            original_status="NOT_UPLOADED",
            latitude=item.latitude,
            longitude=item.longitude,
            captured_at=item.captured_at,
            received_at=now,
        )
        db.add(image)
        db.flush()

        diagnosis = Diagnosis(
            client_uuid=item.diagnosis_client_uuid,
            id_image=image.id,
            id_user=user_id,
            created_date=item.created_date,
            side_leaf=item.side_leaf,
            received_at=now,
            sync_status="METADATA_SYNCED",
        )
        db.add(diagnosis)
        db.flush()

        for leaf_condition in item.detected_leaf_conditions:
            db.add(DetectedLeafCondition(
                id_diagnosis=diagnosis.id,
                id_class=class_map[leaf_condition.id_class_model].id,
                probability=Decimal(str(leaf_condition.probability)),
            ))

        db.commit()
        return {
            "diagnosis_client_uuid": item.diagnosis_client_uuid,
            "image_client_uuid": item.image_client_uuid,
            "status": "METADATA_SYNCED",
            "image_status": "PENDING",
            "id_diagnosis": diagnosis.id,
            "id_image": image.id,
            "message": "Metadatos registrados. Falta cargar la imagen optimizada.",
        }

    except (SyncConflictError, UnknownModelClassError):
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        # Puede ocurrir si dos peticiones intentan registrar el mismo UUID a la vez.
        existing_result = _existing_metadata_result(db, item, user_id)
        if existing_result:
            return existing_result
        raise SyncConflictError("Conflicto al registrar el diagnóstico. Verifica los UUID enviados.")
    except Exception:
        db.rollback()
        raise


