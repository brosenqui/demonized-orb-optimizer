# === Orb Optimizer Makefile ===
# Author: Adam Rosenquist
# Purpose: Setup, run, lint, test, and clean the Orb Optimizer project using uv

# Configurable environment directory (uv defaults to ".venv" if unset)
PROJECT_ENV ?= .venv
UV ?= uv

# Colors
YELLOW := \033[1;33m
GREEN  := \033[1;32m
BLUE   := \033[1;34m
RESET  := \033[0m

# Ensure uv uses our environment path for every command
UV_ENV := UV_PROJECT_ENVIRONMENT=$(PROJECT_ENV)

.PHONY: all install install-prod help run lint typecheck format test clean

all: install

# === Environment Setup ===
install:
	@echo "$(YELLOW)🚀 Creating env and installing project + dev deps (dependency group)...$(RESET)"
	@$(UV_ENV) $(UV) sync --group dev
	@echo "$(GREEN)✅ Environment setup complete!$(RESET)"

install-prod:
	@echo "$(YELLOW)📦 Creating production environment (no dev tools)...$(RESET)"
	@$(UV_ENV) $(UV) sync
	@echo "$(GREEN)✅ Production environment ready!$(RESET)"

# === CLI help / run ===
help:
	@$(UV_ENV) $(UV) run orb-optimize --help

# Pass args via: make run ARGS="optimize --foo bar"
run:
	@echo "$(BLUE)⚙️ Running Orb Optimizer...$(RESET)"
	@$(UV_ENV) $(UV) run orb-optimize optimize $(ARGS)

# === Lint, Type Check, Format, Test ===
lint:
	@echo "$(YELLOW)🔍 Running Ruff...$(RESET)"
	@$(UV_ENV) $(UV) run ruff check orb_optimizer

typecheck:
	@echo "$(YELLOW)🧠 Running MyPy...$(RESET)"
	@$(UV_ENV) $(UV) run mypy orb_optimizer

format:
	@echo "$(YELLOW)🧽 Running Black...$(RESET)"
	@$(UV_ENV) $(UV) run black .

test:
	@echo "$(YELLOW)🧪 Running pytest...$(RESET)"
	@$(UV_ENV) $(UV) run pytest -q

# === Cleanup ===
clean:
	@echo "$(YELLOW)🧹 Cleaning project directories...$(RESET)"
	@rm -rf "$(PROJECT_ENV)" .ruff_cache .mypy_cache .pytest_cache __pycache__ **/__pycache__ build dist .uv-cache
	@echo "$(GREEN)✨ Cleanup complete.$(RESET)"
