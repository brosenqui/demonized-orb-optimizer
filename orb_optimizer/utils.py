"""Utility helpers for the Orb Optimizer.

Includes:
    - ANSI colorized logging setup.
    - Rarity/slot mappings.
    - Helper parsing functions.
"""

import logging
import sys
from typing import Any, TYPE_CHECKING

from .models import ProfileConfig

if TYPE_CHECKING:
    from .data_loader import DataLoader

# === Rarity mappings ===
RARITY_SCORE: dict[str, int] = {
    "Common": 1,
    "Magic": 2,
    "Rare": 3,
    "Heroic": 4,
    "Legendary": 5,
}


# === ANSI color codes for logger ===
class ColorFormatter(logging.Formatter):
    """Custom log formatter with ANSI color codes."""

    COLORS = {
        logging.DEBUG: "\033[92m",  # Green
        logging.INFO: "\033[94m",  # Blue
        logging.WARNING: "\033[93m",  # Yellow
        logging.ERROR: "\033[91m",  # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }

    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure a colorized logger.

    Args:
        verbose: If True, sets log level to DEBUG; otherwise INFO.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger("orb_optimizer")

    # Ensure we don't add duplicate handlers if called multiple times
    if logger.handlers:
        # Update level and return existing
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        return logger

    # Send logs to STDERR so STDOUT can be piped/parsed separately
    handler = logging.StreamHandler(sys.stderr)
    formatter = ColorFormatter("%(asctime)s [%(levelname)s]\t| %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    return logger


# === Helper functions ===
def parse_value(value: Any) -> float:
    """Parse a value that may be a percentage or numeric string.

    Args:
        value: The raw value.

    Returns:
        float: The parsed numeric value.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if value.endswith("%"):
            try:
                return float(value.strip("%"))
            except ValueError:
                return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0

def build_profiles_from_json(loader: "DataLoader", path: str) -> tuple[list[ProfileConfig], list[str]]:
    """Read profiles.json and convert to ProfileConfig list."""
    cfg = loader.load_json(path)
    try:
        profiles_json = cfg["profiles"]
        if not isinstance(profiles_json, list):
            raise TypeError
    except (TypeError, KeyError):
        raise ValueError("profiles.json must contain a 'profiles' array")

    out: list[ProfileConfig] = []
    for pj in profiles_json:
        name = pj["name"]
        set_prio = loader.load_set_priority_or_default(pj.get("set_priority"))
        type_w = loader.load_orb_type_weights_or_default(pj.get("orb_weights"))
        lvl_w = loader.load_orb_level_weights_or_default(pj.get("orb_level_weights"))
        out.append(
            ProfileConfig(
                name=name,
                set_priority=set_prio,
                orb_type_weights=type_w,
                orb_level_weights=lvl_w,
                power=float(pj.get("power", 2.0)),
                epsilon=float(pj.get("epsilon", 0.02)),  # keep aligned with CLI default
                objective=pj.get("objective", "sets-first"),
                weight=float(pj.get("weight", 1.0)),
            )
        )
    shareable = list(cfg.get("shareable_categories", []))
    return out, shareable


def build_default_profile(
    loader: "DataLoader",
    *,
    set_priority_path: str | None,
    orb_weights_path: str | None,
    orb_level_weights_path: str | None,
    objective: str,
    power: float,
    epsilon: float,
) -> ProfileConfig:
    set_prio = loader.load_set_priority_or_default(set_priority_path)
    type_w = loader.load_orb_type_weights_or_default(orb_weights_path)
    lvl_w = loader.load_orb_level_weights_or_default(orb_level_weights_path)
    return ProfileConfig(
        name="DEFAULT",
        set_priority=set_prio,
        orb_type_weights=type_w,
        orb_level_weights=lvl_w,
        power=power,
        epsilon=epsilon,
        objective=objective,
        weight=1.0,
    )