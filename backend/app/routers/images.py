from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..models import Image, Plate
from ..schemas import (
    BatchProcessResponse,
    ImageDetailResponse,
    ImageListResponse,
    ImageResponse,
    PlateCreate,
    PlateResponse,
    ProcessResponse,
)
from ..services.detector import detect_plates
from ..services.redactor import redact_image

router = APIRouter(tags=["images"])


def _require_session(
    x_session_token: str | None = Header(None),
    session_token: str | None = Query(None),
) -> str:
    """Extract session token from header or query parameter."""
    token = x_session_token or session_token
    if not token:
        raise HTTPException(status_code=403, detail="Session token required")
    return token


@router.post("/api/images/upload", response_model=list[ImageResponse])
async def upload_images(
    files: list[UploadFile],
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> list[Image]:
    uploaded: list[Image] = []

    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        ext = Path(file.filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Allowed: {', '.join(settings.allowed_extensions)}",
            )

        contents = await file.read()
        if len(contents) > settings.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} exceeds {settings.max_upload_size // (1024*1024)} MB limit",
            )

        image = Image(
            original_path="",
            filename=file.filename,
            status="pending",
            session_token=token,
        )
        db.add(image)
        await db.flush()

        file_path = f"{image.id}{ext}"
        image.original_path = file_path

        dest = settings.originals_dir / file_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(contents)

        uploaded.append(image)

    await db.commit()
    for image in uploaded:
        await db.refresh(image)
    return uploaded


@router.get("/api/images", response_model=ImageListResponse)
async def list_images(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Image).where(Image.session_token == token).order_by(Image.created_at.desc())
    count_query = select(func.count(Image.id)).where(Image.session_token == token)

    if status:
        query = query.where(Image.status == status)
        count_query = count_query.where(Image.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    images = list(result.scalars().all())

    return {
        "images": images,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/api/images/{image_id}", response_model=ImageDetailResponse)
async def get_image(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> Image:
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.plates))
        .where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    for plate in image.plates:
        plate.corners = json.loads(plate.corners) if isinstance(plate.corners, str) else plate.corners
    return image


@router.delete("/api/images/{image_id}")
async def delete_image(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.plates))
        .where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    original = settings.originals_dir / image.original_path
    if original.exists():
        original.unlink()
    if image.output_path:
        processed = settings.processed_dir / image.output_path
        if processed.exists():
            processed.unlink()

    await db.delete(image)
    await db.commit()
    return {"detail": "Image deleted"}


@router.get("/api/images/{image_id}/original")
async def get_original(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    path = settings.originals_dir / image.original_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")

    return FileResponse(path, filename=image.filename)


@router.post("/api/images/{image_id}/plates", response_model=PlateResponse)
async def create_plate(
    image_id: int,
    plate_data: PlateCreate,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> Plate:
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if len(plate_data.corners) != 4:
        raise HTTPException(status_code=400, detail="Exactly 4 corner points required")

    for corner in plate_data.corners:
        if len(corner) != 2:
            raise HTTPException(status_code=400, detail="Each corner must be [x, y]")

    plate = Plate(
        image_id=image_id,
        corners=json.dumps(plate_data.corners),
        redact_mode=plate_data.redact_mode,
    )
    db.add(plate)

    image.status = "annotated"
    image.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(plate)

    plate.corners = plate_data.corners
    return plate


@router.post("/api/images/{image_id}/detect")
async def detect_plates_endpoint(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    path = settings.originals_dir / image.original_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")

    try:
        plates = detect_plates(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")

    return {"plates": plates}


@router.post("/api/images/{image_id}/process", response_model=ProcessResponse)
async def process_image(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.plates))
        .where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not image.plates:
        raise HTTPException(status_code=400, detail="No plates annotated on this image")

    try:
        await redact_image(
            image, image.plates, settings.originals_dir, settings.processed_dir
        )
        image.output_path = image.original_path
        image.status = "processed"
        image.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"id": image.id, "status": "processed", "message": "Redaction complete"}
    except Exception as e:
        image.status = "error"
        image.updated_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@router.post("/api/images/process-all", response_model=BatchProcessResponse)
async def process_all(
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.plates))
        .where(Image.status.in_(["annotated"]), Image.session_token == token)
    )
    images = list(result.scalars().all())

    results: list[dict] = []
    for image in images:
        if not image.plates:
            continue
        try:
            await redact_image(
                image, image.plates, settings.originals_dir, settings.processed_dir
            )
            image.output_path = image.original_path
            image.status = "processed"
            image.updated_at = datetime.now(timezone.utc)
            results.append({"id": image.id, "status": "processed", "message": "Redaction complete"})
        except Exception as e:
            image.status = "error"
            image.updated_at = datetime.now(timezone.utc)
            results.append({"id": image.id, "status": "error", "message": str(e)})

    await db.commit()
    return {"processed": results, "total": len(results)}


@router.get("/api/images/{image_id}/download")
async def download_image(
    image_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.session_token == token)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not image.output_path:
        raise HTTPException(status_code=400, detail="Image has not been processed yet")

    path = settings.processed_dir / image.output_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Processed file not found")

    name = Path(image.filename).stem + "_redacted" + Path(image.filename).suffix
    return FileResponse(path, filename=name)


@router.post("/api/images/download-all")
async def download_all(
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    result = await db.execute(
        select(Image).where(Image.status == "processed", Image.session_token == token)
    )
    images = list(result.scalars().all())

    if not images:
        raise HTTPException(status_code=404, detail="No processed images available")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for image in images:
            if not image.output_path:
                continue
            path = settings.processed_dir / image.output_path
            if path.exists():
                name = Path(image.filename).stem + "_redacted" + Path(image.filename).suffix
                zf.write(path, name)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=plateblank_redacted.zip"},
    )
