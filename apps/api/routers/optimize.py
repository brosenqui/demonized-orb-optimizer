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
from orb_optimizer.solvers.greedy import GreedyOptimizer

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


def _profile_categories_from(req_profile: OptimizeProfileIn) -> List[Category]:
    """Build Category list for a single OptimizeProfileIn request object."""
    # rarity -> implied slot counts
    if req_profile.categories:
        return [
            Category(name=str(k), slots=CATEGORY_RARITY_SLOTS.get(str(v), 0))
            for k, v in req_profile.categories.items()
        ]
    return []


def _summarize_result_multi(normalized_profiles: List[Dict[str, Any]], combined_score: float | None) -> Dict[str, Any]:
    """Compact UI summary derived from already-normalized profiles."""
    return {
        "combined_score": combined_score,
        "per_profile": [
            {
                "name": p["name"],
                "score": (p.get("set_score") or 0.0) + (p.get("orb_score") or 0.0),
                "set_score": p.get("set_score"),
                "orb_score": p.get("orb_score"),
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
            "profiles": [{ name, score?, set_score?, orb_score? }, ...]
          },
          "raw": {
            "combined_score": number|null,
            "profiles": [
              {
                "name": str,
                "score": number|null,
                "set_score": number|null,
                "orb_score": number|null,
                "used_slots": { [category]: int },
                "assignments": { [category]: [ {type,set,rarity,value,level,slot_index?}, ... ] }
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

    # ---- Inputs ----
    inputs = Inputs(
        orbs=orbs,
        profiles=profiles,
        shareable_categories=req.shareable_categories or None,
    )

    # ---- Solve (greedy unified) ----
    try:
        logger.info("Running unified greedy")
        solver = GreedyOptimizer(inputs=inputs, logger=logger)
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
                        "slot_index": d.get("slot_index"),
                    }
                )
            assignments[str(cat)] = normalized_items

        # used_slots = echo profile config categories
        prof_cfg = next((p for p in profiles if p.name == name), None)
        used_slots = {c.name: int(c.slots) for c in (prof_cfg.categories if prof_cfg else [])}

        # Scores
        set_s = getattr(pr, "set_score", None)
        orb_s = getattr(pr, "orb_score", None)
        total = (set_s if isinstance(set_s, (int, float)) else 0.0) + (orb_s if isinstance(orb_s, (int, float)) else 0.0)

        normalized_profiles.append(
            {
                "name": str(name),
                "score": round(total, 6),
                "set_score": (round(float(set_s), 6) if isinstance(set_s, (int, float)) else None),
                "orb_score": (round(float(orb_s), 6) if isinstance(orb_s, (int, float)) else None),
                "used_slots": used_slots,
                "assignments": assignments,
            }
        )

    summary = _summarize_result_multi(normalized_profiles, combined_round)
    logger.info("Optimization complete")

    # ---- Build final response ----
    res = OptimizeResponse(
        ok=True,
        result=OptimizeResult(
            summary=summary,
            raw={
                "combined_score": combined_round,
                "profiles": normalized_profiles,  # <-- ARRAY, not dict
            },
        ),
    )
    return res
