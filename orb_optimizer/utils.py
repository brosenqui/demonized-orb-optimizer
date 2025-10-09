"""Utility helpers for the Orb Optimizer.

Includes:
    - ANSI colorized logging setup.
    - Rarity/slot mappings.
    - Helper parsing functions.
"""

import logging
import sys
from typing import Any

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
