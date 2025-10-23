# ===== Built-in defaults (for optional knobs) =====

DEFAULT_SET_PRIORITY_WEIGHTS: dict[str, float] = {
    "Leviathan": 8.0,
    "Beezlebub": 6.0,
    "Belphegor": 5.0,
    "Asmodeus": 1.5,
    "Mammon": 1.1,
    "Satan": 1.0,
    "Lucifer": 1.0,
}

# Orb-type multipliers, no bias
DEFAULT_ORB_TYPE_WEIGHTS: dict[str, float] = {
    "Flame": 1.0,
    "Water": 1.0,
    "Wind": 1.0,
    "Earth": 1.0,
    "Sun": 1.0,
    "Grass": 1.0,
    "Lightning": 1.0,
    "Steel": 1.0,
}

# Level caps by rarity
DEFAULT_LEVEL_CAPS: dict[str, int] = {
    "Common": 3,
    "Magic": 3,
    "Rare": 6,
    "Heroic": 6,
    "Legendary": 9,
    "Mythic": 9,
}

# Valid set piece counts
DEFAULT_SET_COUNTS: dict[str, list[int]] = {
    "Lucifer": [4, 5],
    "Mammon": [2, 4, 6],
    "Leviathan": [3, 5, 6],
    "Satan": [4, 5, 6],
    "Asmodeus": [2, 4],
    "Beezlebub": [1, 3, 5],
    "Belphegor": [2, 4, 6],
}

# Additive points per unlocked tier (3/6/9) by orb type
DEFAULT_ORB_LEVEL_WEIGHTS: dict[str, float] = {
    "Flame": 1.0,
    "Water": 1.0,
    "Wind": 1.0,
    "Earth": 1.0,
    "Sun": 1.0,
    "Grass": 1.0,
    "Lightning": 1.0,
    "Steel": 5.0,
}
