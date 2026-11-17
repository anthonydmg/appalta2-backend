
from datetime import datetime, timezone
import logging

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException,
    status
)

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.connection import get_db


from app.config.environment import (
    MAX_IMAGE_SIZE,
    MAX_BATCH_SIZE,
    MAX_BATCH_SIZE_BYTES,
    MAX_OPTIMIZED_BATCH_FILES,
    MAX_OPTIMIZED_IMAGE_SIZE,
    MAX_OPTIMIZED_BATCH_SIZE
)

from app.models.user import User
from app.schemas.diagnosis_sync import (
    DiagnosesSyncRequest,
    DiagnosesSyncResponse,
    DiagnosisSyncResult,
    OptimizedImageBatchResponse,
    DiagnosisSyncStatusResponse,
)

from app.services.auth import get_current_user

from app.services.diagnosis_sync import (
    register_diagnosis_metadata,
    SyncConflictError,
    UnknownModelClassError,
)

from app.services.storage_images import StorageService, InvalidImageError


from app.models.image import Image
from app.models.diagnosis import Diagnosis

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/diagnoses",
    tags=["Diagnoses"]
)
storage = StorageService()

def _error_result(item, message: str):
    return {
        "diagnosis_client_uuid": item.diagnosis_client_uuid,
        "image_client_uuid": item.image_client_uuid,
        "status": "ERROR",
        "image_status": "UNKNOWN",
        "id_diagnosis": None,
        "id_image": None,
        "message": message,
    }
    

@router.post(
    "/sync/metadata",
    response_model=DiagnosesSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar metadatos de diagnósticos",
)
def sync_diagnoses_metadata(
    request: DiagnosesSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = []
    for item in request.diagnoses:
        try:
            result = register_diagnosis_metadata(
                db=db,
                item=item,
                user_id=current_user.id,
            )
        except (SyncConflictError, UnknownModelClassError) as exc:
            result = _error_result(item, str(exc))

            
            print("result:", result)

        except Exception:
            db.rollback()

            logger.exception(
                "ERROR AL REGISTRAR METADATOS - diagnosis_uuid=%s",
                item.diagnosis_client_uuid
            )

            # No enviar detalles internos de PostgreSQL al cliente.
            result = _error_result(
                item,
                "Error interno al registrar los metadatos. Intenta nuevamente.",
            )
        results.append(result)

    registered = sum(1 for r in results if r["status"] in ("METADATA_SYNCED", "SYNCED"))
    return {
        "total_received": len(request.diagnoses),
        "total_registered": registered,
        "total_failed": len(results) - registered,
        "results": results,
    }


@router.post(
    "/images/optimized/batch",
    response_model=OptimizedImageBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Cargar un lote de imágenes optimizadas",
    description=(
        "Recibe hasta 5 imágenes. El nombre de cada archivo debe comenzar "
        "con el UUID de image_client_uuid, por ejemplo UUID.jpg. "
        "Cada imagen se procesa de forma independiente."
    ),
)
def upload_optimized_images_batch(
    files: list[UploadFile] = File(..., description="Hasta 5 imágenes JPG, PNG o WEBP; nombre basado en image_client_uuid"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validación estructural del lote: si está mal formado, no se procesa ninguno.
    if not files:
        raise HTTPException(status_code=400, detail="Debes enviar al menos una imagen.")
    if len(files) > MAX_OPTIMIZED_BATCH_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"El lote admite como máximo {MAX_OPTIMIZED_BATCH_FILES} imágenes.",
        )

    files_by_uuid = {}
    for upload in files:
        safe_filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        try:
            image_uuid = UUID(safe_filename.rsplit(".", 1)[0])
        except (ValueError, AttributeError, IndexError):
            raise HTTPException(
                status_code=422,
                detail=f"Nombre de archivo inválido: {upload.filename!r}. Usa UUID.jpg, UUID.png o UUID.webp.",
            )
        if image_uuid in files_by_uuid:
            raise HTTPException(
                status_code=422,
                detail=f"Se envió más de un archivo para la imagen {image_uuid}.",
            )
        files_by_uuid[image_uuid] = upload

    # Leer y procesar secuencialmente para no mantener todo el lote en memoria.
    total_bytes = 0
    results = []

    for image_uuid, upload in files_by_uuid.items():
        content = upload.file.read(MAX_OPTIMIZED_IMAGE_SIZE + 1)
        total_bytes += len(content)

        if total_bytes > MAX_OPTIMIZED_BATCH_SIZE:
            # Límite total: detener el lote. Los resultados previos siguen siendo válidos.
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": (
                    "Se alcanzó el tamaño máximo total del lote. "
                    "Esta imagen y las siguientes no se procesaron; reintenta con un lote más pequeño."
                ),
            })
            remaining = list(files_by_uuid.items())
            current_index = list(files_by_uuid.keys()).index(image_uuid)
            for remaining_uuid, _ in remaining[current_index + 1:]:
                results.append({
                    "image_client_uuid": remaining_uuid,
                    "status": "ERROR",
                    "diagnosis_status": "UNKNOWN",
                    "message": "No procesada porque se alcanzó el límite total del lote.",
                })
            break

        if not content:
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": "El archivo está vacío.",
            })
            continue

        if len(content) > MAX_OPTIMIZED_IMAGE_SIZE:
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": f"La imagen supera el límite de {MAX_OPTIMIZED_IMAGE_SIZE // (1024 * 1024)} MB.",
            })
            continue

        try:
            image = (
                db.query(Image)
                .join(Diagnosis, Diagnosis.id_image == Image.id)
                .filter(
                    Image.client_uuid == image_uuid,
                    Diagnosis.id_user == current_user.id,
                )
                .with_for_update()
                .first()
            )
        except Exception:
            db.rollback()
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": "No se pudo consultar el registro de la imagen. Intenta nuevamente.",
            })
            continue

        if image is None:
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": "No existe una imagen asociada a un diagnóstico de este usuario.",
            })
            continue

        try:
            diagnosis = (
                db.query(Diagnosis)
                .filter(Diagnosis.id_image == image.id)
                .with_for_update()
                .first()
            )
        except Exception:
            db.rollback()
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": "No se pudo consultar el diagnóstico asociado. Intenta nuevamente.",
            })
            continue

        if diagnosis is None:
            db.rollback()
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "UNKNOWN",
                "message": "No se encontró el diagnóstico asociado a la imagen.",
            })
            continue

        if image.optimized_status == "UPLOADED":
            if image.optimized_storage_path and storage.exists(image.optimized_storage_path):
                results.append({
                    "image_client_uuid": image_uuid,
                    "status": "UPLOADED",
                    "diagnosis_status": diagnosis.sync_status,
                    "id_image": image.id,
                    "id_diagnosis": diagnosis.id,
                    "storage_path": image.optimized_storage_path,
                    "message": "La imagen ya estaba cargada; no se creó un duplicado.",
                })
            else:
                results.append({
                    "image_client_uuid": image_uuid,
                    "status": "ERROR",
                    "diagnosis_status": diagnosis.sync_status,
                    "id_image": image.id,
                    "id_diagnosis": diagnosis.id,
                    "message": "La base de datos indica que la imagen está cargada, pero el archivo no existe en el almacenamiento.",
                })
            db.rollback()
            continue

        storage_key = None
        try:
            saved = storage.save_optimized(image_uuid, content)
            storage_key = saved["storage_key"]

            image.optimized_storage_path = storage_key
            image.optimized_size = saved["size"]
            image.optimized_width = saved["width"]
            image.optimized_height = saved["height"]
            image.optimized_uploaded_at = datetime.now(timezone.utc)
            image.optimized_status = "UPLOADED"
            diagnosis.sync_status = "SYNCED"
            db.commit()

            results.append({
                "image_client_uuid": image_uuid,
                "status": "UPLOADED",
                "diagnosis_status": "SYNCED",
                "id_image": image.id,
                "id_diagnosis": diagnosis.id,
                "storage_path": storage_key,
                "message": "Imagen almacenada correctamente; diagnóstico completamente sincronizado.",
            })
        except InvalidImageError as exc:
            db.rollback()
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "METADATA_SYNCED",
                "id_image": image.id,
                "id_diagnosis": diagnosis.id,
                "message": str(exc),
            })
        except FileExistsError:
            db.rollback()
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "METADATA_SYNCED",
                "id_image": image.id,
                "id_diagnosis": diagnosis.id,
                "message": "Ya existe un archivo para este UUID, pero no figura como cargado. Se requiere reconciliación del almacenamiento.",
            })
        except Exception:
            db.rollback()
            if storage_key:
                try:
                    storage.delete(storage_key)
                except Exception:
                    pass
            results.append({
                "image_client_uuid": image_uuid,
                "status": "ERROR",
                "diagnosis_status": "METADATA_SYNCED",
                "id_image": image.id,
                "id_diagnosis": diagnosis.id,
                "message": "No se pudo almacenar la imagen. Puedes reintentar la carga.",
            })

    total_uploaded = sum(1 for result in results if result["status"] == "UPLOADED")
    return {
        "total_received": len(files),
        "total_uploaded": total_uploaded,
        "total_failed": len(results) - total_uploaded,
        "results": results,
    }


@router.get(
    "/diagnoses/{diagnosis_client_uuid}/sync-status",
    response_model=DiagnosisSyncStatusResponse,
    summary="Consultar el estado de sincronización de un diagnóstico",
)
def get_diagnosis_sync_status(
    diagnosis_client_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diagnosis = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.client_uuid == diagnosis_client_uuid,
            Diagnosis.id_user == current_user.id,
        )
        .first()
    )
    if diagnosis is None:
        raise HTTPException(status_code=404, detail="No se encontró el diagnóstico.")

    image = db.query(Image).filter(Image.id == diagnosis.id_image).first()
    if image is None:
        raise HTTPException(status_code=500, detail="El diagnóstico no tiene una imagen asociada válida.")

    pending_items = []
    if image.optimized_status != "UPLOADED":
        pending_items.append("optimized_image")
    return {
        "diagnosis_client_uuid": diagnosis.client_uuid,
        "image_client_uuid": image.client_uuid,
        "status": diagnosis.sync_status,
        "metadata_status": "REGISTERED",
        "optimized_image_status": image.optimized_status,
        "original_image_status": image.original_status,
        "is_fully_synced": diagnosis.sync_status == "SYNCED",
        "pending_items": pending_items,
    }


@router.get(
    "/{diagnosis_client_uuid}/sync-status",
    response_model=DiagnosisSyncStatusResponse,
    summary="Consultar el estado de sincronización de un diagnóstico",
)
def get_diagnosis_sync_status(
    diagnosis_client_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diagnosis = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.client_uuid == diagnosis_client_uuid,
            Diagnosis.id_user == current_user.id,
        )
        .first()
    )
    if diagnosis is None:
        raise HTTPException(status_code=404, detail="No se encontró el diagnóstico.")

    image = db.query(Image).filter(Image.id == diagnosis.id_image).first()
    if image is None:
        raise HTTPException(status_code=500, detail="El diagnóstico no tiene una imagen asociada válida.")

    pending_items = []
    if image.optimized_status != "UPLOADED":
        pending_items.append("optimized_image")
    return {
        "diagnosis_client_uuid": diagnosis.client_uuid,
        "image_client_uuid": image.client_uuid,
        "status": diagnosis.sync_status,
        "metadata_status": "REGISTERED",
        "optimized_image_status": image.optimized_status,
        "original_image_status": image.original_status,
        "is_fully_synced": diagnosis.sync_status == "SYNCED",
        "pending_items": pending_items,
    }
