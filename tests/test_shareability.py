from __future__ import annotations

import json
from pathlib import Path

import pytest

from orb_optimizer.data_loader import DataLoader
from orb_optimizer.shareability import normalize_shareability_matrix
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


def test_normalize_shareability_matrix_rejects_unknown_keys() -> None:
    with pytest.raises(ValueError, match="unknown categories"):
        normalize_shareability_matrix(
            categories=["Soul"],
            profile_names=["A"],
            shareability_matrix={"Unknown": {"A": True}},
            strict=True,
        )

    with pytest.raises(ValueError, match="unknown profiles"):
        normalize_shareability_matrix(
            categories=["Soul"],
            profile_names=["A"],
            shareability_matrix={"Soul": {"B": True}},
            strict=True,
        )


def test_build_profiles_migrates_legacy_shareable_list_to_matrix(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    payload = {
        "profiles": [
            {
                "name": "A",
                "categories": {"Soul": "Rare"},
            },
            {
                "name": "B",
                "categories": {"Soul": "Rare"},
            },
        ],
        "shareable_categories": ["Soul"],
    }
    profiles_path.write_text(json.dumps(payload), encoding="utf-8")

    profiles, matrix = build_profiles_from_json(
        DataLoader(_NullLogger()),
        str(profiles_path),
        default_slots={"Soul": 1},
    )

    assert [profile.name for profile in profiles] == ["A", "B"]
    assert matrix == {"Soul": {"A": True, "B": True}}
