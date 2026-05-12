from __future__ import annotations

from pathlib import Path

from orb_optimizer.data_loader import DataLoader
from orb_optimizer.models import Category, Inputs, Orb, ProfileConfig
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


def test_greedy_enforces_set_cap_and_returns_partial() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(6),
        profiles=[_make_profile("P1", slots=6)],
        shareable_categories=None,
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
    assert lucifer_count <= 5
    assert profile.requested_slots == 6
    assert profile.filled_slots == 5
    assert profile.is_partial is True
    assert result.is_partial is True


def test_greedy_shared_slots_respect_per_profile_set_cap() -> None:
    inputs = Inputs(
        orbs=_make_lucifer_orbs(6),
        profiles=[_make_profile("P1", slots=6), _make_profile("P2", slots=6)],
        shareable_categories=["Soul"],
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
        assert lucifer_count <= 5
        assert profile.is_partial is True


def test_greedy_restarts_are_non_regressive() -> None:
    logger = _NullLogger()
    loader = DataLoader(logger)
    root = Path(__file__).resolve().parents[1]
    orbs = loader.load_orbs(root / "data" / "orbs.json")
    slots = loader.load_json(root / "data" / "slots.json")
    profiles, shareable = build_profiles_from_json(
        loader, str(root / "data" / "profiles.json"), default_slots=slots
    )
    inputs = Inputs(orbs=orbs, profiles=profiles, shareable_categories=shareable)

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
        orbs=_make_lucifer_orbs(6),
        profiles=[_make_profile("P1", slots=6)],
        shareable_categories=None,
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
    assert lucifer_count <= 5
    assert profile.requested_slots == 6
    assert profile.filled_slots <= 5
    assert profile.is_partial is True
    assert result.is_partial is True
