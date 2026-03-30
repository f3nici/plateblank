from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")
    session_token: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    plates: Mapped[list[Plate]] = relationship(
        "Plate", back_populates="image", cascade="all, delete-orphan"
    )


class Plate(Base):
    __tablename__ = "plates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False
    )
    corners: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of 4 [x,y] pairs
    redact_mode: Mapped[str] = mapped_column(Text, default="white")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    image: Mapped[Image] = relationship("Image", back_populates="plates")
