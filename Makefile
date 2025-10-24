# === Orb Optimizer Makefile ===
# Author: Adam Rosenquist
# Purpose: Setup, run, lint, test, and clean the Orb Optimizer project using uv

# ----------------------------
# Config
# ----------------------------
PROJECT_ENV ?= .venv
UV ?= uv
WEB_DIR ?= web
NPM ?= npm

# Default data paths (override on CLI: make run-beam ORBS=... SLOTS=... PROFILES=...)
ORBS     ?= data/orbs.json
SLOTS    ?= data/slots.json
PROFILES ?= data/profiles.json

# Beam/Greedy defaults (override: make run-beam BEAM=400 TOPK=50)
BEAM ?= 200
TOPK ?= 20
REFINE_PASSES ?= 2
REFINE_REPORT ?= 0 # 1 to enable --refine-report

# Colors
YELLOW := \033[1;33m
GREEN  := \033[1;32m
BLUE   := \033[1;34m
RESET  := \033[0m

# Ensure uv uses our environment path for every command
UV_ENV := UV_PROJECT_ENVIRONMENT=$(PROJECT_ENV)

# Node (for optional web tasks)
NPM ?= npm
WEB_DIR ?= web

# ----------------------------
# Phony targets
# ----------------------------
.PHONY: all help \
        install install-core install-api install-cli install-all install-prod \
        run-beam run-greedy run help-cli \
        api api-prod api-docs \
        web-dev web-build web-preview serve \
        lint typecheck format test clean

all: install

# ----------------------------
# Environment Setup
# ----------------------------

## Full dev env: core + dev tools; add extras as needed via install-api/install-cli
install:
	@echo "$(YELLOW)🚀 Creating env and installing project + dev tools (dependency group)...$(RESET)"
	@$(UV_ENV) $(UV) sync --group dev
	@echo "$(GREEN)✅ Environment setup complete!$(RESET)"

## Core only (no API/CLI extras, still includes dev tools)
install-core:
	@echo "$(YELLOW)📦 Installing core only (no api/cli extras)...$(RESET)"
	@$(UV_ENV) $(UV) sync --group dev --no-extra
	@echo "$(GREEN)✅ Core installed.$(RESET)"

## Add FastAPI extras to the current env
install-api:
	@echo "$(YELLOW)🌐 Adding FastAPI extras...$(RESET)"
	@$(UV_ENV) $(UV) sync --extra api
	@echo "$(GREEN)✅ API extras installed.$(RESET)"

## Add CLI extras to the current env
install-cli:
	@echo "$(YELLOW)🛠  Adding CLI extras...$(RESET)"
	@$(UV_ENV) $(UV) sync --extra cli
	@echo "$(GREEN)✅ CLI extras installed.$(RESET)"

## Everything (core + api + cli) with dev tools
install-all:
	@echo "$(YELLOW)🧰 Installing core + API + CLI + dev tools...$(RESET)"
	@$(UV_ENV) $(UV) sync --group dev --extra api --extra cli
	@echo "$(GREEN)✅ All extras installed.$(RESET)"

## Production env (no dev tools); add desired extras
install-prod:
	@echo "$(YELLOW)📦 Creating production environment...$(RESET)"
	@$(UV_ENV) $(UV) sync --extra api --extra cli
	@echo "$(GREEN)✅ Production environment ready!$(RESET)"

# ----------------------------
# CLI
# ----------------------------

## Show CLI help
help-cli:
	@$(UV_ENV) $(UV) run orb-optimize --help

## Run BEAM search (default subcommand for service parity)
## Example overrides:
##   make run-beam BEAM=400 TOPK=50 ORBS=data/orbs.json SLOTS=data/slots.json PROFILES=data/profiles.json
run-beam:
	@echo "$(BLUE)⚙️ Running Orb Optimizer (beam) ...$(RESET)"
	@$(UV_ENV) $(UV) run orb-optimize --orbs $(ORBS) --slots $(SLOTS) --profiles $(PROFILES) beam --beam $(BEAM) --topk $(TOPK) $$( [ "$(REFINE_REPORT)" = "1" ] && printf -- '--refine-report' ) --refine-passes $(REFINE_PASSES)

## Run GREEDY search
run-greedy:
	@echo "$(BLUE)⚙️ Running Orb Optimizer (greedy) ...$(RESET)"
	@$(UV_ENV) $(UV) run orb-optimize --orbs $(ORBS) --slots $(SLOTS) --profiles $(PROFILES) greedy

# ----------------------------
# API (FastAPI service)
# ----------------------------

## Dev server with auto-reload (requires install-api)
api:
	@echo "$(BLUE)🌐 Starting FastAPI (dev, reload) on :8000 ...$(RESET)"
	@$(UV_ENV) $(UV) run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

## Prod-ish server (no reload, one worker by default).
## For real prod, front with a process manager and set workers via --workers N.
api-prod:
	@echo "$(BLUE)🚀 Starting FastAPI (prod) on :8000 ...$(RESET)"
	@$(UV_ENV) $(UV) run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

## OpenAPI docs quick-open (requires `open` on macOS; otherwise just visit the URL)
api-docs:
	@echo "$(BLUE)📖 OpenAPI docs at http://localhost:8000/docs$(RESET)"
	@([ "$$(command -v open)" ] && open http://localhost:8000/docs) || true

# ----------------------------
# Website (Vite + React)
# ----------------------------

## Install frontend deps
web-install:
	@echo "$(YELLOW)📦 Installing frontend dependencies...$(RESET)"
	@cd $(WEB_DIR) && $(NPM) install
	@echo "$(GREEN)✅ Frontend dependencies installed.$(RESET)"

## Run Vite dev server (proxies to FastAPI)
web-dev:
	@echo "$(BLUE)🧩 Starting web dev server (Vite)...$(RESET)"
	@cd $(WEB_DIR) && $(NPM) run dev

## Build static bundle to web/dist
web-build:
	@echo "$(BLUE)🧱 Building frontend for production...$(RESET)"
	@cd $(WEB_DIR) && $(NPM) run build
	@echo "$(GREEN)✅ web/dist ready.$(RESET)"

## Preview built bundle (serves dist on localhost:4173)
web-preview:
	@echo "$(BLUE)👀 Previewing built bundle...$(RESET)"
	@cd $(WEB_DIR) && $(NPM) run preview

## Build web and serve via FastAPI's static mount
serve: web-build
	@echo "$(BLUE)🖥 Serving built web via FastAPI on :8000 ...$(RESET)"
	@$(UV_ENV) $(UV) run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# ----------------------------
# Quality: Lint / Typecheck / Format / Test
# ----------------------------

lint:
	@echo "$(YELLOW)🔍 Running Ruff...$(RESET)"
	@$(UV_ENV) $(UV) run ruff check orb_optimizer apps tests

typecheck:
	@echo "$(YELLOW)🧠 Running MyPy...$(RESET)"
	@$(UV_ENV) $(UV) run mypy orb_optimizer apps

format:
	@echo "$(YELLOW)🧽 Running Black...$(RESET)"
	@$(UV_ENV) $(UV) run black .

test:
	@echo "$(YELLOW)🧪 Running pytest...$(RESET)"
	@$(UV_ENV) $(UV) run pytest -q

# ----------------------------
# Cleanup
# ----------------------------

clean:
	@echo "$(YELLOW)🧹 Cleaning project directories...$(RESET)"
	@rm -rf "$(PROJECT_ENV)" .ruff_cache .mypy_cache .pytest_cache __pycache__ **/__pycache__ build dist .uv-cache
	@echo "$(GREEN)✨ Cleanup complete.$(RESET)"
