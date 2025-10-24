# ============================
# Stage 1: Build the frontend
# ============================
FROM node:20-alpine AS webbuilder
WORKDIR /app/web
COPY web/ ./

# Install deps (honor lockfile if present)
RUN if [ -f pnpm-lock.yaml ]; then \
      npm -g i pnpm && pnpm i --frozen-lockfile; \
    elif [ -f yarn.lock ]; then \
      npm -g i yarn && yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
      npm ci; \
    else \
      npm i; \
    fi

# Optional: override API base at build time
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
    PATH="/opt/venv/bin:$PATH"

# OS deps for uv install and SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y && \
    /root/.local/bin/uv --version

WORKDIR /app

# Copy only files needed to resolve dependency graph (best cache use)
COPY pyproject.toml uv.lock* ./

# Create venv and sync only dependencies (not the project code yet)
RUN /root/.local/bin/uv venv "$VIRTUAL_ENV" && \
    /root/.local/bin/uv sync --no-dev --no-install-project

# ===========================================
# Stage 3: Runtime (app + prebuilt web + venv)
# ===========================================
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Minimal OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the prebuilt Python venv (deps) from pydeps stage
COPY --from=pydeps /opt/venv /opt/venv

# Copy app source
COPY . .

# Install your app **only** (deps already present in venv)
# Using pip here is fine; it won't reinstall deps due to --no-deps.
RUN pip install --upgrade pip && \
    pip install "uvicorn[standard]" "gunicorn" && \
    pip install --no-deps .

# Copy built frontend
COPY --from=webbuilder /app/web/dist ./web_dist

# Render runtime vars
ENV PORT=8080 \
    APP_MODULE=apps.api.main:app \
    FRONTEND_DIST=/app/web_dist

# Healthcheck (FastAPI should expose /healthz)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# Start with gunicorn (Render will provide $PORT)
CMD exec gunicorn "$APP_MODULE" \
    --bind 0.0.0.0:"$PORT" \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120
