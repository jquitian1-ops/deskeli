# ============================================================================
# Dockerfile - DeskEli / TicketDesk Enterprise
# Producción: Gunicorn + eventlet (WebSocket-ready)
# Multi-stage para imagen pequeña sin compiladores en runtime.
# ============================================================================

# ────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — compila wheels con toolchain completo
# ────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependencias para compilar:
# - gcc / build-essential: compilar paquetes con extensiones C
# - libffi-dev / libssl-dev: cryptography
# - libpq-dev: psycopg2 (PostgreSQL en futuro)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalar a un prefijo local para copiar al runtime
RUN pip install --no-cache-dir --user --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — imagen mínima, sin toolchain
# ────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Librerías de runtime + wget para healthcheck (más liviano que curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    wget \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN useradd -m -u 1000 deskeli

# Copiar dependencias Python desde el builder
COPY --from=builder /root/.local /home/deskeli/.local

# Copiar el código
COPY --chown=deskeli:deskeli . .

# Carpetas que deben existir y ser escribibles. En Coolify, mapeá volúmenes a:
#   /app/instance  (BD SQLite)
#   /app/uploads   (adjuntos)
#   /app/backups   (backups cifrados)
#   /app/logs      (access/error log)
RUN mkdir -p /app/instance /app/uploads /app/backups /app/logs && \
    chown -R deskeli:deskeli /app

USER deskeli

ENV PATH=/home/deskeli/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py \
    GUNICORN_BIND=0.0.0.0:5050 \
    GUNICORN_WORKERS=1 \
    TZ=America/Bogota

# Healthcheck contra el endpoint /api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:5050/api/health || exit 1

EXPOSE 5050

# Producción: Gunicorn con eventlet (WebSocket-ready) + preload_app
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:application"]
