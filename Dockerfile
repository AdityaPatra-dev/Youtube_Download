# ==============================================================================
# YouTube Playlist & Media Downloader — Production Dockerfile
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

# Install essential system dependencies:
# - ffmpeg: stream remuxing, audio extraction, chapter embedding & partial salvage
# - nodejs: YouTube EJS challenge solver (prevents HTTP 403 Forbidden bot detection)
# - aria2: multi-connection socket acceleration for maximum download throughput
# - curl & ca-certificates: health check probing & secure TLS connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    aria2 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Layer cache: install Python requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY app.py download_playlist.py ./
COPY static/ ./static/

# Prepare download destination folder
RUN mkdir -p /app/downloads

# Expose container port
EXPOSE 8000

# Declare persistent volume mount for downloaded media
VOLUME ["/app/downloads"]

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/system || exit 1

# Launch the FastAPI web server
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8000"]

