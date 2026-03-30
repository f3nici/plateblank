# CLAUDE.md — PlateBlank

## Project Overview

PlateBlank is a self-hosted web tool for manually redacting number plates from vehicle photos. Users upload images, click four corners of each plate on a canvas, and the backend renders a blur or white-fill redaction. Runs in a single Docker container.

## Tech Stack

- **Frontend**: Vue 3 (Composition API, `<script setup>`), Vite, Tailwind CSS
- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLAlchemy (async + aiosqlite), OpenCV, Pillow
- **Database**: SQLite (WAL mode) at `/app/data/plateblank.db`
- **Container**: Single multi-stage Dockerfile

## Project Structure

```
backend/app/          — FastAPI application
  main.py             — app factory, CORS, lifespan, static mount
  config.py           — Settings class (paths, DB URL, upload limits)
  database.py         — async engine, sessionmaker, Base
  models.py           — Image, Plate ORM models
  schemas.py          — Pydantic models for request/response
  routers/images.py   — upload, list, detail, delete, process, download
  routers/plates.py   — plate annotation CRUD
  services/redactor.py — OpenCV quad masking (blur + white fill)

frontend/src/         — Vue 3 SPA
  views/              — UploadView, AnnotateView, ResultsView
  components/         — ImageCanvas (annotation), ThumbnailGrid, PlateOverlay
  api.js              — axios instance with base URL and error interceptor
  router.js           — vue-router config
```

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install
npm run dev          # dev server with proxy to :8000
npm run build        # production build → frontend/dist/

# Docker
docker build -t plateblank:latest .
docker run -p 8000:8000 -v plateblank_data:/app/data plateblank:latest

# Lint / Format
cd backend && ruff check . && ruff format .
cd frontend && npx eslint src/ && npx prettier --write src/
```

## Code Conventions

### Python (backend)
- Use `async def` for all route handlers and DB operations.
- Type-hint every function signature. Use Pydantic models for all request/response bodies.
- One router file per resource (images, plates). Keep business logic in `services/`.
- Raise `HTTPException` with specific status codes — never return bare dicts with error messages.
- Use `pathlib.Path` for all filesystem operations, never string concatenation.
- Store plate corner coordinates in **natural image pixel space** (not display-scaled CSS pixels).
- Keep imports sorted: stdlib → third-party → local, separated by blank lines.
- Use `from __future__ import annotations` in every file.

### Vue / JavaScript (frontend)
- Composition API with `<script setup>` exclusively — no Options API.
- One component per file, PascalCase filenames.
- Use `ref()` and `reactive()` — no `this`.
- Keep API calls in `api.js`, never call axios/fetch directly from components.
- Canvas operations in `ImageCanvas.vue` must convert between CSS display coordinates and natural image coordinates using the image's `naturalWidth`/`naturalHeight`.
- Tailwind for styling — no scoped CSS unless absolutely necessary for canvas layering.

### General
- No authentication, no user accounts. This is a single-user tool.
- No ML or auto-detection. Plate marking is manual only.
- All images served through API endpoints, never by direct filesystem path.
- SQLite only. No Postgres, no external DB.
- Error responses are always `{ "detail": "human readable message" }`.

## Critical Implementation Details

### Canvas Coordinate Mapping
The annotation canvas displays images scaled to fit the viewport. All corner coordinates stored in the DB must be in the original image's pixel space. The frontend must:
1. Track the current scale factor: `scale = canvas.width / image.naturalWidth`
2. On click: `realX = event.offsetX / scale`, `realY = event.offsetY / scale`
3. On render: `displayX = realX * scale`, `displayY = realY * scale`

### Redaction with OpenCV
```python
corners_np = np.array(corners, dtype=np.int32)
mask = np.zeros(image.shape[:2], dtype=np.uint8)
cv2.fillConvexPoly(mask, corners_np, 255)
```
This handles angled/rotated plates natively — no special rotation logic needed.

### File Storage
```
/app/data/originals/{image_id}.{ext}   — uploaded files
/app/data/processed/{image_id}.{ext}   — redacted outputs
/app/data/plateblank.db                — SQLite database
```
The `/app/data` directory must be a mounted volume for persistence.

## Testing Approach

- Backend: pytest + httpx async test client. Test upload, annotation save, redaction output.
- Frontend: manual testing is fine — no unit test requirement.
- Always test with images of varying sizes and aspect ratios.
- Test with multiple plates per image.
- Test angled plates (the whole point of quad selection).

## Things to Avoid

- Don't add nginx, Caddy, or any reverse proxy — Uvicorn serves everything.
- Don't add user auth or sessions.
- Don't use localStorage for image data — everything goes through the API.
- Don't use `cv2.imread` to load uploads — use `PIL.Image.open()` then convert to numpy array for OpenCV, so format support is broader.
- Don't put the SQLite DB outside `/app/data/`.
- Don't use `latest` as a hardcoded image tag in the workflow — it's set via workflow input.
