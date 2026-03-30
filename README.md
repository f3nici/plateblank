# PlateBlank

Self-hosted tool for manually redacting number plates from vehicle photos. Upload a batch of images, click the four corners of each plate, and PlateBlank renders a blur or white-fill redaction — handles plates at any angle.

## Quick Start

```bash
docker run -d \
  --name plateblank \
  -p 8000:8000 \
  -v plateblank_data:/app/data \
  ghcr.io/YOUR_USERNAME/plateblank:latest
```

Open `http://localhost:8000` in your browser.

## How It Works

1. **Upload** — drag-and-drop or pick JPG/PNG/WebP images (batch supported)
2. **Annotate** — click the four corners of each plate (TL → TR → BR → BL) on a zoomable canvas
3. **Process** — hit "Process All" to render redactions
4. **Download** — grab individual images or a ZIP of everything

## Building from Source

```bash
# Development
cd frontend && npm install && npm run dev    # Vue dev server on :5173
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload  # API on :8000

# Docker
docker build -t plateblank:latest .
docker run -p 8000:8000 -v plateblank_data:/app/data plateblank:latest
```

## GitHub Actions

The included workflow builds and pushes the Docker image to GHCR. Trigger it manually from the Actions tab and type your desired image tag (e.g. `1.0.0`, `latest`).

## Data Persistence

Mount `/app/data` as a volume. It contains the SQLite database, uploaded originals, and processed outputs.

## Stack

Vue 3 · Vite · Tailwind CSS · FastAPI · SQLite · OpenCV · Pillow · Docker
