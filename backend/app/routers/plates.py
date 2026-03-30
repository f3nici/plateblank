from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Plate

router = APIRouter(tags=["plates"])


@router.delete("/api/plates/{plate_id}")
async def delete_plate(plate_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Plate).where(Plate.id == plate_id))
    plate = result.scalar_one_or_none()
    if not plate:
        raise HTTPException(status_code=404, detail="Plate not found")

    await db.delete(plate)
    await db.commit()
    return {"detail": "Plate deleted"}
