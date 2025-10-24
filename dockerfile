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


# ===========================================
# Stage 2: Runtime (Python + app + web_dist)
# ===========================================
FROM python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Minimal OS deps (curl only for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only files needed to build/install first (better layer caching)
COPY pyproject.toml ./
COPY README.MD ./

# Copy source
# Your pyproject uses hatch with:
# [tool.hatch.build.targets.wheel]
# packages = ["src/orb_optimizer", "apps"]
COPY src ./src
COPY apps ./apps

# Install the project WITH the 'api' extra (brings fastapi + uvicorn)
# This installs both your code and all dependencies in one step.
RUN pip install --no-cache-dir '.[api]'

# Bring in the built frontend
COPY --from=webbuilder /app/web/dist ./web_dist

# Runtime configuration
ENV PORT=8080 \
    APP_MODULE=apps.api.main:app \
    FRONTEND_DIST=/app/web_dist

# Healthcheck (uses PORT if provided by the platform)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8080}/health" || exit 1'

# Start the API using env vars; make uvicorn PID 1
CMD sh -c 'exec python -m uvicorn "$APP_MODULE" --host 0.0.0.0 --port "${PORT:-8080}"'
