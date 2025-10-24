# ---- Stage 1: Build frontend (Vite + React) ----
FROM node:20-alpine AS webbuilder

WORKDIR /app
# Only copy web first to leverage Docker layer caching
COPY web/package.json web/package-lock.json* web/pnpm-lock.yaml* web/yarn.lock* ./web/ 2>/dev/null || true
COPY web/ ./web/

WORKDIR /app/web
# Prefer a lockfile if present; fall back to npm install
RUN if [ -f pnpm-lock.yaml ]; then \
      npm -g i pnpm && pnpm i --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
      npm -g i yarn && yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm i; \
    fi

# Make sure the app builds with same-origin API
# If you need a custom API base, set VITE_API_BASE_URL at build time.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL="${VITE_API_BASE_URL}"
RUN npm run build

# Output will be at /app/web/dist


# ---- Stage 2: Backend runtime (FastAPI + Uvicorn via Gunicorn) ----
FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (build tools kept minimal; add gcc if you have native deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend + pyproject first (for caching), then the rest
COPY pyproject.toml README* ./
COPY orb_optimizer ./orb_optimizer
COPY apps ./apps

# Install backend deps (build from pyproject)
RUN pip install --upgrade pip \
 && pip install "uvicorn[standard]" "gunicorn" \
 && pip install .

# Copy built frontend from stage 1
COPY --from=webbuilder /app/web/dist ./web_dist

# Expose nothing explicitly; Render will inject $PORT and map it
ENV PORT=8080 \
    APP_MODULE=apps.api.main:app \
    FRONTEND_DIST=/app/web_dist

# Simple healthcheck hitting /healthz (you can change to /api/health if you expose one)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
 CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# Start with gunicorn + uvicorn workers, binding to $PORT (Render requirement)
CMD exec gunicorn "$APP_MODULE" \
    --bind 0.0.0.0:"$PORT" \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120
