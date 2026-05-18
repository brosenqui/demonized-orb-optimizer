# apps/api/routers/optimize.py
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request
from logging import Logger

from apps.api.schemas import OptimizeRequest, OptimizeResponse, OptimizeResult, OptimizeProfileIn
from orb_optimizer.io.loader import Loader
from orb_optimizer.io.sources import DictSource
from orb_optimizer.models import Inputs, ProfileConfig, Category
from orb_optimizer.shareability import normalize_shareability_matrix
from orb_optimizer.solvers.greedy import GreedyOptimizer
from orb_optimizer.shared_summary import shared_summary_to_dict

router = APIRouter()

# Map rarity -> slots for profile-local "category_rarity" inputs
CATEGORY_RARITY_SLOTS: Dict[str, int] = {
    "Rare": 1,
    "Epic": 2,
    "Legendary": 3,
    "Mythic": 4,
}


# ---------------- Helpers ----------------

def _dc_to_dict(obj: Any) -> Any:
    """Defensive serializer for dataclasses/objects -> plain types."""
    if dataclasses.is_dataclass(obj):
        return {k: _dc_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _dc_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dc_to_dict(v) for v in obj]
    if hasattr(obj, "__dict__"):
        try:
            return {k: _dc_to_dict(v) for k, v in vars(obj).items()}
        except Exception:
            pass
    return obj

def _as_non_negative_int(value: Any) -> int:
    try:
        numeric = int(float(value))
    except Exception:
        return 0
    return max(0, numeric)


def _profile_categories_from(req_profile: OptimizeProfileIn) -> List[Category]:
    """Build Category list for a single OptimizeProfileIn request object."""
    if req_profile.slots:
        return [
            Category(name=str(k), slots=max(0, int(v)))
            for k, v in req_profile.slots.items()
        ]
    # rarity -> implied slot counts
    if req_profile.categories:
        return [
            Category(name=str(k), slots=CATEGORY_RARITY_SLOTS.get(str(v), 0))
            for k, v in req_profile.categories.items()
        ]
    return []


def _summarize_result_multi(
    normalized_profiles: List[Dict[str, Any]],
    combined_score: float | None,
    *,
    is_partial: bool,
    shared_summary: Dict[str, Any] | None,
    run_diagnostics: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """Compact UI summary derived from already-normalized profiles."""
    return {
        "combined_score": combined_score,
        "is_partial": is_partial,
        "shared_summary": shared_summary,
        "run_diagnostics": run_diagnostics,
        "profiles": [
            {
                "name": p["name"],
                "score": (p.get("set_score") or 0.0) + (p.get("orb_score") or 0.0),
                "set_score": p.get("set_score"),
                "orb_score": p.get("orb_score"),
                "is_partial": p.get("is_partial", False),
            }
            for p in normalized_profiles
        ],
    }


# ---------------- Route ----------------

@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, request: Request) -> OptimizeResponse:
    """
    Canonical greedy-only route.
    Always returns:
      {
        "ok": true,
        "result": {
          "summary": {
            "combined_score": number|null,
            "is_partial": bool,
            "profiles": [{ name, score?, set_score?, orb_score? }, ...]
          },
          "raw": {
            "combined_score": number|null,
            "is_partial": bool,
            "profiles": [
              {
                "name": str,
                "score": number|null,
                "set_score": number|null,
                "orb_score": number|null,
                "is_partial": bool,
                "assignments": { [category]: [ {type,set,rarity,value,level,awakened,slot_index?}, ... ] }
              },
              ...
            ]
          }
        }
      }
    """
    logger: Logger = request.app.state.logger
    loader = Loader(logger)
    logger.info("Received optimization request (multi-profile)")

    # ---- Orbs ----
    try:
        orbs = loader.load_orbs(DictSource([o.model_dump(by_alias=True) for o in req.orbs]))
    except Exception as e:
        logger.exception("Failed to parse orbs")
        raise HTTPException(status_code=400, detail=f"Invalid orbs: {e}")

    # ---- Profiles (with per-profile categories) ----
    profiles: List[ProfileConfig] = []
    for p in req.profiles:
        cats = _profile_categories_from(p)
        profiles.append(
            ProfileConfig(
                name=p.name,
                weight=p.weight,
                objective=p.objective,
                power=p.power,
                epsilon=p.epsilon,
                set_priority=p.set_priority,
                orb_type_weights=p.orb_weights,
                orb_level_weights=p.orb_level_weights,
                categories=cats,
            )
        )

    profile_names = [profile.name for profile in profiles]
    if len(set(profile_names)) != len(profile_names):
        raise HTTPException(status_code=400, detail="Profile names must be unique for shareability_matrix keys.")
    categories = sorted({category.name for profile in profiles for category in profile.categories})

    try:
        shareability_matrix = normalize_shareability_matrix(
            categories=categories,
            profile_names=profile_names,
            shareability_matrix=req.shareability_matrix,
            strict=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # ---- Inputs ----
    inputs = Inputs(
        orbs=orbs,
        profiles=profiles,
        shareability_matrix=shareability_matrix,
    )

    # ---- Solve (greedy unified) ----
    try:
        logger.info("Running unified greedy")
        solver = GreedyOptimizer(
            inputs=inputs,
            logger=logger,
            topk_per_type=16,
            restarts=6,
            seed=0,
            max_time_ms=1500,
            enable_debug_breakdown=False,
        )
        # Expect the solver to return an object with:
        #   result.combined_score: float
        #   result.profiles: dict[name] -> object with set_score, orb_score, loadout: {cat: [Orb,...]}
        result = solver.optimize()
    except Exception as e:
        logger.exception("Solver failed")
        raise HTTPException(status_code=500, detail=f"Solver failed: {e}")

    # ---- Canonicalize response shape (profiles as array; use assignments key) ----
    combined = getattr(result, "combined_score", None)
    combined_round = round(float(combined), 6) if isinstance(combined, (int, float)) else None
    is_partial = bool(getattr(result, "is_partial", False))
    shared_summary = shared_summary_to_dict(getattr(result, "shared_summary", None))
    run_diagnostics = getattr(result, "run_diagnostics", None) or None

    normalized_profiles: List[Dict[str, Any]] = []
    # result.profiles expected as dict[name] -> data
    raw_profiles = getattr(result, "profiles", {}) or {}
    for name, pr in raw_profiles.items():
        # pr.loadout is expected as { category: [Orb, ...] }
        loadout = getattr(pr, "loadout", None) or getattr(pr, "assignments", None) or {}

        # Normalize Orbs to plain dicts with canonical keys
        assignments: Dict[str, List[Dict[str, Any]]] = {}
        for cat, items in (loadout.items() if isinstance(loadout, dict) else []):
            normalized_items: List[Dict[str, Any]] = []
            for it in items or []:
                # Support dataclass/object or dict
                d = _dc_to_dict(it)
                normalized_items.append(
                    {
                        "type": d.get("type"),
                        "set": d.get("set") or d.get("set_name"),
                        "rarity": d.get("rarity"),
                        "value": d.get("value"),
                        "level": d.get("level"),
                        "awakened": _as_non_negative_int(d.get("awakened", 0)),
                        "slot_index": d.get("slot_index"),
                    }
                )
            assignments[str(cat)] = normalized_items

        # Scores
        set_s = getattr(pr, "set_score", None)
        orb_s = getattr(pr, "orb_score", None)
        total = (set_s if isinstance(set_s, (int, float)) else 0.0) + (orb_s if isinstance(orb_s, (int, float)) else 0.0)
        req_slots = int(getattr(pr, "requested_slots", 0) or 0)
        fill_slots = int(getattr(pr, "filled_slots", 0) or 0)
        partial = bool(getattr(pr, "is_partial", fill_slots < req_slots))

        normalized_profiles.append(
            {
                "name": str(name),
                "score": round(total, 6),
                "set_score": (round(float(set_s), 6) if isinstance(set_s, (int, float)) else None),
                "orb_score": (round(float(orb_s), 6) if isinstance(orb_s, (int, float)) else None),
                "is_partial": partial,
                "assignments": assignments,
            }
        )

    summary = _summarize_result_multi(
        normalized_profiles,
        combined_round,
        is_partial=is_partial,
        shared_summary=shared_summary,
        run_diagnostics=run_diagnostics,
    )
    logger.info("Optimization complete")

    # ---- Build final response ----
    res = OptimizeResponse(
        ok=True,
        result=OptimizeResult(
            summary=summary,
            raw={
                "combined_score": combined_round,
                "is_partial": is_partial,
                "shared_summary": shared_summary,
                "run_diagnostics": run_diagnostics,
                "profiles": normalized_profiles,  # <-- ARRAY, not dict
            },
        ),
    )
    return res
