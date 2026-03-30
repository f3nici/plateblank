# ---- Stage 1: Build Vue frontend ----
FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Production image ----
FROM python:3.12-slim

# Install OpenCV system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into backend static directory
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

# Create data directories
RUN mkdir -p /app/data/originals /app/data/processed

# Non-root user
RUN useradd -m -r plateblank && \
    chown -R plateblank:plateblank /app
USER plateblank

EXPOSE 8000

VOLUME ["/app/data"]

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
