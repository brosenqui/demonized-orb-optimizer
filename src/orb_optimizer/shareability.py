from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional, Sequence, Set


def matrix_from_shareable_categories(
    *,
    categories: Sequence[str],
    profile_names: Sequence[str],
    shareable_categories: Optional[Iterable[str]],
) -> Dict[str, Dict[str, bool]]:
    enabled = {str(name) for name in (shareable_categories or [])}
    return {
        str(category): {str(profile): str(category) in enabled for profile in profile_names}
        for category in categories
    }


def normalize_shareability_matrix(
    *,
    categories: Sequence[str],
    profile_names: Sequence[str],
    shareability_matrix: Optional[Mapping[str, Mapping[str, object]]],
    strict: bool,
) -> Dict[str, Dict[str, bool]]:
    category_set = {str(category) for category in categories}
    profile_set = {str(profile) for profile in profile_names}

    raw_matrix = shareability_matrix or {}
    if strict:
        unknown_categories = sorted(str(category) for category in raw_matrix.keys() if str(category) not in category_set)
        if unknown_categories:
            raise ValueError(
                f"shareability_matrix contains unknown categories: {', '.join(unknown_categories)}"
            )
        unknown_profiles: Set[str] = set()
        for row in raw_matrix.values():
            unknown_profiles.update(str(profile) for profile in row.keys() if str(profile) not in profile_set)
        if unknown_profiles:
            raise ValueError(
                "shareability_matrix contains unknown profiles: "
                + ", ".join(sorted(unknown_profiles))
            )

    normalized: Dict[str, Dict[str, bool]] = {}
    for category in categories:
        row_raw = raw_matrix.get(category, {})
        row: Dict[str, bool] = {}
        for profile in profile_names:
            row[profile] = bool(row_raw.get(profile, False))
        normalized[category] = row
    return normalized


def enabled_profiles_by_category(
    matrix: Mapping[str, Mapping[str, bool]] | None,
) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for category, row in (matrix or {}).items():
        enabled = {profile for profile, value in row.items() if bool(value)}
        if enabled:
            out[category] = enabled
    return out
