# ============================
# Stage 1: Build the frontend
# ============================
FROM node:20-alpine AS webbuilder
WORKDIR /app/web
COPY web/ ./

RUN if [ -f pnpm-lock.yaml ]; then \
      npm -g i pnpm && pnpm i --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
      npm -g i yarn && yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm i; \
    fi

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL="${VITE_API_BASE_URL}"
RUN npm run build
# -> /app/web/dist

# ==============================================
# Stage 2: Build Python deps with uv (venv only)
# ==============================================
FROM python:3.11-slim AS pydeps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:$PATH" \
    UV_INSTALL_DIR=/usr/local/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install uv (no -y)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && uv --version

WORKDIR /app
COPY pyproject.toml uv.lock* README* ./

# Build venv with deps only
# If you don't have uv.lock committed, remove --frozen
RUN uv venv "$VIRTUAL_ENV" && uv sync --extra api

# ===========================================
# Stage 3: Runtime (app + prebuilt web + venv)
# ===========================================
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy prebuilt Python venv (deps)
COPY --from=pydeps /opt/venv /opt/venv

# Copy app source
COPY . .

# Install your app only (deps already in venv)
RUN pip install --upgrade pip && \
    pip install "uvicorn[standard]" "gunicorn" && \
    pip install --no-deps .

# Copy built frontend
COPY --from=webbuilder /app/web/dist ./web_dist

ENV PORT=8080 \
    APP_MODULE=apps.api.main:app \
    FRONTEND_DIST=/app/web_dist

# Healthcheck (your health route can be elsewhere; adjust path if needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

CMD exec gunicorn "$APP_MODULE" \
    --bind 0.0.0.0:"$PORT" \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120
