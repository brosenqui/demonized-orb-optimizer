# ===== Built-in defaults (for optional knobs) =====

DEFAULT_SET_PRIORITY_WEIGHTS: dict[str, float] = {
    "Leviathan": 1.0,
    "Beelzebub": 1.0,
    "Belphegor": 1.0,
    "Asmodeus": 1.0,
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
    "Epic": 6,
    "Legendary": 9,
    "Mythic": 9,
}

# Valid set piece counts
DEFAULT_SET_COUNTS: dict[str, list[int]] = {
    "Lucifer": [4, 5, 6],
    "Mammon": [2, 4, 6],
    "Leviathan": [3, 5, 6],
    "Satan": [4, 5, 6],
    "Asmodeus": [2, 4],
    "Beelzebub": [1, 3, 5],
    "Belphegor": [2, 4, 6],
}

# Per-set tier bonuses by threshold.
# Values are display-oriented and can also be used for diagnostics/analytics.
DEFAULT_SET_TIER_BONUSES: dict[str, dict[int, dict[str, float]]] = {
    "Lucifer": {
        4: {"Stun Chance %": 2.0},
        5: {"Stun Chance %": 2.5},
        6: {"Stun Chance %": 3.0},
    },
    "Mammon": {
        2: {"Set ATK %": 300.0},
        4: {"Set ATK %": 550.0},
        6: {"Set ATK %": 1000.0},
    },
    "Leviathan": {
        3: {"Set HP %": 25.0},
        5: {"Set HP %": 50.0},
        6: {"Set HP %": 100.0},
    },
    "Satan": {
        4: {"Silence Chance %": 1.5},
        5: {"Silence Chance %": 2.0},
        6: {"Silence Chance %": 2.5},
    },
    "Asmodeus": {
        2: {"Set Accuracy %": 50.0},
        4: {"Set Accuracy %": 100.0},
    },
    "Beelzebub": {
        1: {"Mythic Skill Damage Amp %": 50.0},
        3: {"Mythic Skill Damage Amp %": 100.0},
        5: {"Mythic Skill Damage Amp %": 200.0},
    },
    "Belphegor": {
        2: {"Passive Skill Amplification %": 5.0},
        4: {"Passive Skill Amplification %": 10.0},
        6: {"Passive Skill Amplification %": 15.0},
    },
}

# Multipliers applied to cumulative level-gate values (3/6/9) by orb type
DEFAULT_ORB_LEVEL_WEIGHTS: dict[str, float] = {
    "Flame": 1.0,
    "Water": 1.0,
    "Wind": 1.0,
    "Earth": 1.0,
    "Sun": 1.0,
    "Grass": 1.0,
    "Lightning": 1.0,
    "Steel": 1.0,
}

# Level gate values by orb type.
# Gates are cumulative at level >=3, >=6, >=9.
# Missing/unknown gates currently carry forward the last known value.
DEFAULT_ORB_LEVEL_GATE_VALUES: dict[str, dict[int, float]] = {
    "Flame": {3: 100.0, 6: 125.0, 9: 200.0},
    "Water": {3: 2.0, 6: 2.0, 9: 3.0},
    "Wind": {3: 15.0, 6: 15.0, 9: 15.0},
    "Earth": {3: 30.0, 6: 40.0, 9: 50.0},
    "Sun": {3: 3.0, 6: 4.0, 9: 5.0},
    "Grass": {3: 25.0, 6: 50.0, 9: 100.0},
    "Lightning": {3: 15.0, 6: 20.0, 9: 30.0},
    "Steel": {3: 3.0, 6: 4.0, 9: 5.0},
}
