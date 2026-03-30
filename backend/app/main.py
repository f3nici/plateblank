from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .database import engine
from .models import Base
from .routers import images, plates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create data directories
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.originals_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable WAL mode
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # Migrate: add session_token column if missing
        result = await conn.execute(text("PRAGMA table_info(images)"))
        columns = [row[1] for row in result]
        if "session_token" not in columns:
            await conn.execute(
                text("ALTER TABLE images ADD COLUMN session_token TEXT")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_images_session_token ON images (session_token)")
            )

    yield

    await engine.dispose()


app = FastAPI(title="PlateBlank", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router)
app.include_router(plates.router)


@app.exception_handler(413)
async def request_entity_too_large(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": "File too large"},
    )


# Serve Vue frontend in production
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    # Serve built assets (JS, CSS, etc.)
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA catch-all: serve index.html for any non-API route
    @app.get("/{path:path}")
    async def serve_spa(path: str) -> FileResponse:
        file_path = frontend_dist / path
        if file_path.is_file() and ".." not in path:
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
