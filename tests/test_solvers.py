from __future__ import annotations

from pathlib import Path

from orb_optimizer.defaults import (
    DEFAULT_ORB_LEVEL_GATE_VALUES,
    DEFAULT_SET_COUNTS,
    DEFAULT_SET_PRIORITY_WEIGHTS,
)
from orb_optimizer.data_loader import DataLoader
from orb_optimizer.models import AssignedOrb, Category, Inputs, Orb, ProfileConfig
from orb_optimizer.orb_level_bonus import cumulative_gate_value_for_orb
from orb_optimizer.reporter import OptimizationReporter
from orb_optimizer.solvers.beam import UnifiedOptimizer
from orb_optimizer.solvers.greedy import GreedyOptimizer
from orb_optimizer.utils import build_profiles_from_json


class _NullLogger:
    def debug(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def info(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def warning(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def error(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


def _make_profile(name: str, slots: int) -> ProfileConfig:
    return ProfileConfig(
        name=name,
        objective="sets-first",
        set_priority={"Lucifer": 5.0},
        orb_type_weights={
            "Flame": 1.0,
            "Water": 1.0,
            "Wind": 1.0,
            "Earth": 1.0,
            "Sun": 1.0,
            "Grass": 1.0,
            "Lightning": 1.0,
            "Steel": 1.0,
        },
        orb_level_weights={},
        power=2.0,
        epsilon=0.0,
        weight=1.0,
        categories=[Category(name="Soul", slots=slots)],
    )


def _make_types_first_level_profile(name: str) -> ProfileConfig:
    return ProfileConfig(
        name=name,
        objective="types-first",
        set_priority={},
        orb_type_weights={"Flame": 0.0},
        orb_level_weights={"Flame": 1.0},
        power=2.0,
        epsilon=0.0,
        weight=1.0,
        categories=[Category(name="Soul", slots=1)],
    )


def _make_lucifer_orbs(count: int) -> list[Orb]:
    types = ["Flame", "Water", "Wind", "Earth", "Sun", "Grass", "Lightning", "Steel"]
    out: list[Orb] = []
    for idx in range(count):
        out.append(
            Orb(
                type=types[idx % len(types)],
                set="Lucifer",
                rarity="Rare",
                value=float(100 - idx),
                level=1,
                awakened=0,
            )
        )
    return out


def _all_enabled_matrix(
    *,
    category: str,
    profiles: list[str],
) -> dict[str, dict[str, bool]]:
    return {category: {profile: True for profile in profiles}}


def test_greedy_enforces_set_cap_and_returns_partial() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(7),
        profiles=[_make_profile("P1", slots=7)],
        shareability_matrix=None,
    )
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=inputs,
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()

    profile = result.profiles["P1"]
    lucifer_count = sum(1 for group in profile.loadout.values() for orb in group if orb.set == "Lucifer")
    assert lucifer_count <= 6
    assert profile.requested_slots == 7
    assert profile.filled_slots == 6
    assert profile.is_partial is True
    assert result.is_partial is True
    assert result.run_diagnostics.get("algorithm") == "greedy"
    assert result.run_diagnostics.get("set_cap_rejections", 0) >= 1


def test_greedy_shared_slots_respect_per_profile_set_cap() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(7),
        profiles=[_make_profile("P1", slots=7), _make_profile("P2", slots=7)],
        shareability_matrix=_all_enabled_matrix(category="Soul", profiles=["P1", "P2"]),
    )
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=inputs,
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()

    for name in ("P1", "P2"):
        profile = result.profiles[name]
        lucifer_count = sum(1 for group in profile.loadout.values() for orb in group if orb.set == "Lucifer")
        assert lucifer_count <= 6
        assert profile.is_partial is True

    assert result.shared_summary is not None
    assert result.shared_summary.requested_slots <= 7
    assert result.shared_summary.filled_slots <= 6
    assert result.shared_summary.requested_positions <= 14
    assert result.shared_summary.filled_positions <= 12
    assert set(result.shared_summary.compromise_loss_by_profile.keys()) == {"P1", "P2"}
    assert sum(result.shared_summary.active_sets.values()) == result.shared_summary.filled_slots

    p1_values = [
        orb.value
        for group in result.profiles["P1"].loadout.values()
        for orb in group
    ]
    assert abs(sum(result.shared_summary.totals_by_type.values()) - sum(p1_values)) < 1e-9


def test_greedy_restarts_are_non_regressive() -> None:
    logger = _NullLogger()
    loader = DataLoader(logger)
    root = Path(__file__).resolve().parents[1]
    orbs = loader.load_orbs(root / "data" / "orbs.json")
    slots = loader.load_json(root / "data" / "slots.json")
    profiles, shareable = build_profiles_from_json(
        loader, str(root / "data" / "profiles.json"), default_slots=slots
    )
    inputs = Inputs(orbs=orbs, profiles=profiles, shareability_matrix=shareable)

    baseline = GreedyOptimizer(
        logger=logger,
        inputs=inputs,
        topk_per_type=16,
        restarts=0,
        max_time_ms=5000,
        seed=0,
    ).optimize()
    improved = GreedyOptimizer(
        logger=logger,
        inputs=inputs,
        topk_per_type=16,
        restarts=6,
        max_time_ms=5000,
        seed=0,
    ).optimize()

    assert improved.combined_score >= baseline.combined_score


def test_beam_enforces_set_cap_and_returns_partial() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(7),
        profiles=[_make_profile("P1", slots=7)],
        shareability_matrix=None,
    )
    result = UnifiedOptimizer(
        logger=_NullLogger(),
        inputs=inputs,
        topk_per_category=20,
        parallelism="serial",
        max_time_ms=5000,
    ).optimize(beam_width=100)

    profile = result.profiles["P1"]
    lucifer_count = sum(1 for group in profile.loadout.values() for orb in group if orb.set == "Lucifer")
    assert lucifer_count <= 6
    assert profile.requested_slots == 7
    assert profile.filled_slots <= 6
    assert profile.is_partial is True
    assert result.is_partial is True
    assert result.run_diagnostics.get("algorithm") == "beam"
    assert result.run_diagnostics.get("set_cap_rejections", 0) >= 1


def test_beam_populates_shared_summary() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(7),
        profiles=[_make_profile("P1", slots=7), _make_profile("P2", slots=7)],
        shareability_matrix=_all_enabled_matrix(category="Soul", profiles=["P1", "P2"]),
    )
    result = UnifiedOptimizer(
        logger=_NullLogger(),
        inputs=inputs,
        topk_per_category=20,
        parallelism="serial",
        max_time_ms=5000,
    ).optimize(beam_width=100)

    assert result.shared_summary is not None
    assert result.shared_summary.requested_slots <= 7
    assert result.shared_summary.requested_positions <= 14
    assert result.shared_summary.filled_positions <= 12
    assert set(result.shared_summary.compromise_loss_by_profile.keys()).issubset({"P1", "P2"})


def test_greedy_strict_sharing_applies_to_all_checked_profiles() -> None:
    profiles = [_make_profile("A", slots=1), _make_profile("B", slots=1), _make_profile("C", slots=1)]
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Rare", value=100.0, level=1, awakened=0),
        Orb(type="Water", set="Lucifer", rarity="Rare", value=80.0, level=1, awakened=0),
    ]
    matrix = {
        "Soul": {
            "A": True,
            "B": True,
            "C": True,
        }
    }
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=profiles, shareability_matrix=matrix),
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()

    a_orb = result.profiles["A"].loadout["Soul"][0]
    b_orb = result.profiles["B"].loadout["Soul"][0]
    c_orb = result.profiles["C"].loadout["Soul"][0]

    assert (a_orb.type, a_orb.value) == (b_orb.type, b_orb.value)
    assert (b_orb.type, b_orb.value) == (c_orb.type, c_orb.value)


def test_greedy_allows_subset_sharing_per_slot() -> None:
    profiles = [_make_profile("A", slots=1), _make_profile("B", slots=1), _make_profile("C", slots=1)]
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Rare", value=100.0, level=1, awakened=0),
        Orb(type="Water", set="Lucifer", rarity="Rare", value=80.0, level=1, awakened=0),
    ]
    matrix = {
        "Soul": {
            "A": True,
            "B": True,
            "C": False,
        }
    }
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=profiles, shareability_matrix=matrix),
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()

    a_orb = result.profiles["A"].loadout["Soul"][0]
    b_orb = result.profiles["B"].loadout["Soul"][0]
    c_orb = result.profiles["C"].loadout["Soul"][0]

    assert (a_orb.type, a_orb.value) == (b_orb.type, b_orb.value)
    assert c_orb.type != a_orb.type
    assert result.shared_summary is not None
    assert result.shared_summary.totals_by_type == {a_orb.type: a_orb.value}
    assert sum(result.shared_summary.active_sets.values()) == 1


def test_greedy_prioritizes_sharing_enabled_subset_before_solo() -> None:
    profiles = [_make_profile("C", slots=1), _make_profile("A", slots=1), _make_profile("B", slots=1)]
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Rare", value=100.0, level=1, awakened=0),
        Orb(type="Water", set="Lucifer", rarity="Rare", value=80.0, level=1, awakened=0),
    ]
    matrix = {
        "Soul": {
            "A": True,
            "B": True,
            "C": False,
        }
    }
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=profiles, shareability_matrix=matrix),
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()

    a_orb = result.profiles["A"].loadout["Soul"][0]
    b_orb = result.profiles["B"].loadout["Soul"][0]
    c_orb = result.profiles["C"].loadout["Soul"][0]

    assert (a_orb.type, a_orb.value) == ("Flame", 100.0)
    assert (b_orb.type, b_orb.value) == ("Flame", 100.0)
    assert (c_orb.type, c_orb.value) == ("Water", 80.0)


def test_beam_strict_sharing_applies_to_all_checked_profiles() -> None:
    profiles = [_make_profile("A", slots=1), _make_profile("B", slots=1), _make_profile("C", slots=1)]
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Rare", value=100.0, level=1, awakened=0),
        Orb(type="Water", set="Lucifer", rarity="Rare", value=80.0, level=1, awakened=0),
    ]
    matrix = {
        "Soul": {
            "A": True,
            "B": True,
            "C": True,
        }
    }
    result = UnifiedOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=profiles, shareability_matrix=matrix),
        topk_per_category=20,
        parallelism="serial",
        max_time_ms=5000,
    ).optimize(beam_width=100)

    a_orb = result.profiles["A"].loadout["Soul"][0]
    b_orb = result.profiles["B"].loadout["Soul"][0]
    c_orb = result.profiles["C"].loadout["Soul"][0]

    assert (a_orb.type, a_orb.value) == (b_orb.type, b_orb.value)
    assert (b_orb.type, b_orb.value) == (c_orb.type, c_orb.value)


def test_beam_allows_subset_sharing_per_slot() -> None:
    profiles = [_make_profile("A", slots=1), _make_profile("B", slots=1), _make_profile("C", slots=1)]
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Rare", value=100.0, level=1, awakened=0),
        Orb(type="Water", set="Lucifer", rarity="Rare", value=80.0, level=1, awakened=0),
    ]
    matrix = {
        "Soul": {
            "A": True,
            "B": True,
            "C": False,
        }
    }
    result = UnifiedOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=profiles, shareability_matrix=matrix),
        topk_per_category=20,
        parallelism="serial",
        max_time_ms=5000,
    ).optimize(beam_width=100)

    a_orb = result.profiles["A"].loadout["Soul"][0]
    b_orb = result.profiles["B"].loadout["Soul"][0]
    c_orb = result.profiles["C"].loadout["Soul"][0]

    assert (a_orb.type, a_orb.value) == (b_orb.type, b_orb.value)
    assert c_orb.type != a_orb.type
    assert result.shared_summary is not None
    assert result.shared_summary.totals_by_type == {a_orb.type: a_orb.value}
    assert sum(result.shared_summary.active_sets.values()) == 1


def test_defaults_include_beelzebub_spelling() -> None:
    assert "Beelzebub" in DEFAULT_SET_COUNTS
    assert DEFAULT_SET_COUNTS["Beelzebub"] == [1, 3, 5]
    assert "Beelzebub" in DEFAULT_SET_PRIORITY_WEIGHTS
    assert "Beezlebub" not in DEFAULT_SET_COUNTS
    assert "Beezlebub" not in DEFAULT_SET_PRIORITY_WEIGHTS


def test_reporter_active_set_contrib_uses_profile_power() -> None:
    profile = ProfileConfig(
        name="P1",
        objective="sets-first",
        set_priority={"Beelzebub": 2.0},
        orb_type_weights={},
        orb_level_weights={},
        power=2.0,
        epsilon=0.0,
        weight=1.0,
        categories=[Category(name="Soul", slots=5)],
    )
    loadout = {
        "Soul": [
            AssignedOrb(type="Flame", set="Beelzebub", rarity="Rare", level=0, value=0.0),
            AssignedOrb(type="Water", set="Beelzebub", rarity="Rare", level=0, value=0.0),
            AssignedOrb(type="Wind", set="Beelzebub", rarity="Rare", level=0, value=0.0),
            AssignedOrb(type="Earth", set="Beelzebub", rarity="Rare", level=0, value=0.0),
            AssignedOrb(type="Sun", set="Beelzebub", rarity="Rare", level=0, value=0.0),
        ]
    }

    rows = OptimizationReporter(use_colors=False)._active_sets_table(loadout, profile)
    row = next(r for r in rows if r["set"] == "Beelzebub")
    assert row["tiers"] == 3
    assert row["contrib"] == 18.0  # weight(2) * tiers(3)^power(2)


def test_orb_level_gate_bonus_uses_base_level_only() -> None:
    orb = Orb(type="Earth", set="Lucifer", rarity="Legendary", value=0.0, level=2, awakened=99)
    assert cumulative_gate_value_for_orb(orb) == 0.0

    orb.level = 6
    assert cumulative_gate_value_for_orb(orb) == 70.0

    orb.level = 9
    assert cumulative_gate_value_for_orb(orb) == 120.0


def test_default_orb_level_gate_values_include_latest_known_values() -> None:
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Flame"] == {3: 100.0, 6: 125.0, 9: 200.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Water"] == {3: 2.0, 6: 2.0, 9: 3.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Wind"] == {3: 15.0, 6: 15.0, 9: 15.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Earth"] == {3: 30.0, 6: 40.0, 9: 50.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Sun"] == {3: 3.0, 6: 4.0, 9: 5.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Lightning"] == {3: 15.0, 6: 20.0, 9: 30.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Grass"] == {3: 25.0, 6: 50.0, 9: 100.0}
    assert DEFAULT_ORB_LEVEL_GATE_VALUES["Steel"] == {3: 3.0, 6: 4.0, 9: 5.0}


def test_greedy_level_gate_choice_ignores_awakened_levels() -> None:
    profile = _make_types_first_level_profile("P1")
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Legendary", value=10.0, level=2, awakened=9),
        Orb(type="Flame", set="Lucifer", rarity="Legendary", value=10.0, level=3, awakened=0),
    ]
    result = GreedyOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=[profile], shareability_matrix=None),
        topk_per_type=16,
        restarts=0,
        max_time_ms=3000,
        seed=0,
    ).optimize()
    selected = result.profiles["P1"].loadout["Soul"][0]
    assert selected.level == 3


def test_beam_level_gate_choice_ignores_awakened_levels() -> None:
    profile = _make_types_first_level_profile("P1")
    orbs = [
        Orb(type="Flame", set="Lucifer", rarity="Legendary", value=10.0, level=2, awakened=9),
        Orb(type="Flame", set="Lucifer", rarity="Legendary", value=10.0, level=3, awakened=0),
    ]
    result = UnifiedOptimizer(
        logger=_NullLogger(),
        inputs=Inputs(orbs=orbs, profiles=[profile], shareability_matrix=None),
        topk_per_category=20,
        parallelism="serial",
        max_time_ms=5000,
    ).optimize(beam_width=50)
    selected = result.profiles["P1"].loadout["Soul"][0]
    assert selected.level == 3
