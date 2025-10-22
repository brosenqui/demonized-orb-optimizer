# 🧮 The Demonized Orb Optimizer

A command-line optimizer for calculating the **best possible orb loadouts** in *The Demonized*.

Supports multiple solver strategies — including a **beam search optimizer** for maximum precision and a **greedy optimizer** for fast, approximate results.

---

## 🚀 Setup

### 1️⃣ Install Python 3.11

> Python 3.11.x is required.

Download from [python.org](https://www.python.org/downloads/release/python-3119/).

### 2️⃣ Install `uv`

Install [Astral’s `uv`](https://github.com/astral-sh/uv), a modern, fast package manager:

```bash
# macOS (Homebrew)
brew install uv

# or via Astral’s official installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3️⃣ Install dependencies

```bash
make install
```

This will:

* Create a `.venv` virtual environment  
* Install runtime + dev dependencies (`uv sync --group dev`)  
* Prepare the CLI (`orb-optimize`) for immediate use  

For a production-only setup (no linting/testing tools):

```bash
make install-prod
```

---

## 🧱 Makefile Commands

| Command | Description |
|----------|-------------|
| `make install` | Create `.venv` and install all dependencies (`uv sync --group dev`) |
| `make install-prod` | Create `.venv` and install runtime-only dependencies |
| `make run` | Run the optimizer CLI (pass args via `ARGS="..."`) |
| `make lint` | Run Ruff linter |
| `make typecheck` | Run MyPy static type checks |
| `make format` | Run Black code formatter |
| `make test` | Run Pytest suite |
| `make clean` | Remove the virtual environment and build caches |

---

## ⚙️ CLI Overview

The Orb Optimizer CLI supports **multiple solver strategies**, each as a dedicated subcommand:

| Command | Description |
|----------|-------------|
| `uv run orb-optimize ... optimize` | Runs the **Beam Search** solver (precision-focused) |
| `uv run orb-optimize ... greedy` | Runs the **Greedy** solver (fast heuristic-based) |

📝 *All global input options (like `--orbs`, `--slots`, `--profiles`) must come **before** the solver name.*

---

## 📂 Input Files & Defaults

The optimizer requires orb and slot data, and can optionally load custom weighting and configuration files.  
If optional files are missing, **built-in defaults** are used automatically.

| File | Required | CLI Option | Description | Fallback Behavior |
|------|-----------|-------------|--------------|--------------------|
| `orbs.json` | ✅ Yes | `--orbs` | List of orb definitions (`type`, `set`, `rarity`, `value`, `level`, etc.) | Must exist. |
| `slots.json` | ✅ Yes | `--slots` | Defines category names and slot counts per rarity. | Must exist. |
| `set_priority.json` | ❌ Optional | `--set-priority` | Maps orb sets → priority weights. | Uses `DEFAULT_SET_PRIORITY_WEIGHTS`. |
| `orb_weights.json` | ❌ Optional | `--orb-weights` | Maps orb type → weighting multiplier. | Uses `DEFAULT_ORB_TYPE_WEIGHTS`. |
| `orb_level_weights.json` | ❌ Optional | `--orb-level-weights` | Orb type → additive bonus per tier (3/6/9). | Uses `DEFAULT_ORB_LEVEL_WEIGHTS`. |
| `profiles.json` | ❌ Optional | `--profiles` | Defines multiple optimization profiles with weights and parameters. | If omitted, a single “default” profile is synthesized. |

---

## 🧠 Example Usage

### 🌀 Run the Beam (Precise) Optimizer

```bash
uv run orb-optimize \
  --profiles ./data/profiles.json \
  --orbs ./data/orbs.json \
  --slots ./data/slots.json \
  beam \
  --beam 200 \
  --topk 20 \
  --refine-passes 2 \
  --refine-report

```

### ⚡ Run the Greedy (Fast) Optimizer

```bash
uv run orb-optimize \
  --profiles ./data/profiles.json \
  --orbs ./data/orbs.json \
  --slots ./data/slots.json \
  greedy 
```

Greedy mode is significantly faster and suitable for experimentation or large datasets.

---

## 👥 Multi-Profile Optimization (`profiles.json`)

You can run multiple weighted optimization profiles simultaneously.  
Each profile defines its own scoring weights, objective preference, and power coefficients.

Example:

```json
{
  "profiles": [
    {
      "name": "PVP",
      "objective": "types-first",
      "power": 2.0,
      "epsilon": 0.02,
      "weight": 1.0,
      "set_priority": "data/set_priority_dps.json",
      "orb_weights": "data/orb_weights_dps.json",
      "orb_level_weights": "data/orb_level_weights_dps.json"
    },
    {
      "name": "PVE",
      "objective": "sets-first",
      "power": 2.5,
      "epsilon": 0.01,
      "weight": 0.8,
      "set_priority": "data/set_priority_clearspeed.json",
      "orb_weights": "data/orb_weights_clearspeed.json",
      "orb_level_weights": "data/orb_level_weights_clearspeed.json"
    }
  ],
  "shareable_categories": [
    "Wings",
    "Wagon",
    "Beast"
  ]
}
```

**Explanation:**
- Each entry in `"profiles"` defines a full scoring profile.  
- The `"weight"` field determines its contribution to the combined score.  
- `"objective"` determines whether **set completion** or **orb quality** is prioritized.  
- `"shareable_categories"` lists categories that all profiles share the same orbs for (e.g., shared inventory).

You can reference other JSON weight files, or omit them to use defaults.

---

## 🧰 Development Tools

Installed automatically with `make install`:

* 🧹 **Ruff** — Linting and style enforcement  
* 🧠 **MyPy** — Type checking  
* ⚙️ **Black** — Code formatting  
* 🧪 **Pytest** — Unit testing  

Run checks manually:

```bash
make lint
make typecheck
make format
make test
```

---

## 🧾 License

MIT License © 2025  
The Demonized Orb Optimizer project is open-source and community maintained.
