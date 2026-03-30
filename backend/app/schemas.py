from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlateCreate(BaseModel):
    corners: list[list[float]] = Field(..., min_length=4, max_length=4)
    redact_mode: Literal["white", "blur", "color_match"] = "color_match"


class PlateResponse(BaseModel):
    id: int
    image_id: int
    corners: list[list[float]]
    redact_mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImageDetailResponse(ImageResponse):
    plates: list[PlateResponse] = []


class ImageListResponse(BaseModel):
    images: list[ImageResponse]
    total: int
    page: int
    per_page: int


class ProcessResponse(BaseModel):
    id: int
    status: str
    message: str


class BatchProcessResponse(BaseModel):
    processed: list[ProcessResponse]
    total: int
