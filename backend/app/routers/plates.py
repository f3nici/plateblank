from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Plate

router = APIRouter(tags=["plates"])


def _require_session(
    x_session_token: str | None = Header(None),
    session_token: str | None = Query(None),
) -> str:
    """Extract session token from header or query parameter."""
    token = x_session_token or session_token
    if not token:
        raise HTTPException(status_code=403, detail="Session token required")
    return token


@router.delete("/api/plates/{plate_id}")
async def delete_plate(
    plate_id: int,
    token: str = Depends(_require_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Plate).options(selectinload(Plate.image)).where(Plate.id == plate_id)
    )
    plate = result.scalar_one_or_none()
    if not plate:
        raise HTTPException(status_code=404, detail="Plate not found")

    if plate.image.session_token != token:
        raise HTTPException(status_code=404, detail="Plate not found")

    await db.delete(plate)
    await db.commit()
    return {"detail": "Plate deleted"}
