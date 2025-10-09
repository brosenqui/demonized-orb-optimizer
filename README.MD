# 🧮 The Demonized Orb Optimizer

A tool for calculating the **optimal orb loadout** in the mobile game The Demonized.  

---

### 🚀 Setup

First, install `uv` globally (if you haven’t already):

```bash
# macOS (Homebrew)
brew install uv

# or Astral’s official installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, run:

```bash
make install
```

This will:

* Create a `.venv` virtual environment
* Install all project + dev dependencies (via `uv sync --group dev`)
* Prepare the optimizer for immediate use

For a production-only environment (no dev tools):

```bash
make install-prod
```

---

### 🧱 Makefile Commands

| Command | Description |
|----------|-------------|
| `make install` | Create `.venv` and install all dependencies (`uv sync --group dev`) |
| `make install-prod` | Create `.venv` and install runtime dependencies only |
| `make run` | Run the optimizer CLI (use `ARGS="..."` to pass options) |
| `make lint` | Run Ruff linter |
| `make typecheck` | Run MyPy type checker |
| `make format` | Run Black code formatter |
| `make test` | Run the Pytest suite |
| `make clean` | Remove virtual environment and build caches |

---

### ⚙️ Example Usage

Run the optimizer via the Makefile:

```bash
make run ARGS="--orbs ./data/orbs.json --slots ./data/slots.json --mode beam"
```

Or manually with `uv`:

```bash
uv run orb-optimize optimize --orbs ./data/orbs.json --slots ./data/slots.json
```

---

### 📂 File Inputs & Defaults

Orb Optimizer expects several JSON files to describe your configuration.  
Some are required (core game data), others are optional (preferences, weights, or level data).  
If an optional file is missing, **built-in defaults** are used.

| File | Required | CLI Option | Description | Fallback Behavior |
|------|-----------|-------------|--------------|--------------------|
| `orbs.json` | ✅ Yes | `--orbs` | List of orb definitions (`type`, `set`, `rarity`, `value`, etc.). | Must exist. |
| `slots.json` | ✅ Yes | `--slots` | Defines rarity categories and their slot counts. | Must exist. |
| `weights.json` | ❌ Optional | `--weights` | Overrides set preference multipliers. | Falls back to `DEFAULT_SET_WEIGHTS`. |
| `orb_weights.json` | ❌ Optional | `--orb-weights` | Adjusts orb type importance. | Falls back to `DEFAULT_ORB_TYPE_WEIGHTS`. |
| `orb_levels.json` | ❌ Optional | `--orb-levels` | Defines rarity → max level caps. | Falls back to `DEFAULT_LEVEL_CAPS`. |
| `orb_level_weights.json` | ❌ Optional | `--orb-level-weights` | Defines additive bonus per tier. | Falls back to `DEFAULT_ORB_LEVEL_WEIGHTS`. |

---

### 🧠 Example CLI Usage

```bash
orb-optimize optimize --orbs ./data/orbs.json --slots ./data/slots.json --weights ./data/weights.json --orb-weights ./data/orb_weights.json --orb-levels ./data/orb_levels.json --orb-level-weights ./data/orb_level_weights.json
```

Or rely on built-in defaults:

```bash
orb-optimize optimize --orbs ./orbs.json --slots ./slots.json
```

When optional files are missing, the optimizer logs a ⚠️ warning and uses defaults from `data_loader.py`.

---

### 🧰 Development Tools

Installed automatically when you run `make install`:

* 🧹 **Ruff** — Linting and code style enforcement  
* 🧠 **MyPy** — Static type checking  
* ⚙️ **Black** — Code formatting  
* 🧪 **Pytest** — Unit testing framework  

Run checks manually:

```bash
make lint
make typecheck
make test
```

---

### 🧩 Developer Notes

1. **Dependencies**
   * Runtime dependencies: `[project.dependencies]` in `pyproject.toml`
   * Dev dependencies: `[dependency-groups].dev` in `pyproject.toml`
   * Update versions or add new ones directly in `pyproject.toml`

2. **Package Management**
   * `uv` compiles and caches all dependencies locally under `.uv-cache`
   * Virtual environment stored in `.venv`
   * Safe to delete `.venv` and rerun `make install` anytime

3. **Linting & Formatting**
   * Ruff enforces modern Python style rules
   * Black reformats the codebase:
     ```bash
     uv run black orb_optimizer
     ```

---

## 🧾 License

MIT License © 2025
