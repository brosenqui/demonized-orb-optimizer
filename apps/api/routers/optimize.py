# apps/api/routers/optimize.py
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request

from apps.api.schemas import OptimizeRequest, OptimizeResponse, OptimizeResult
from orb_optimizer.io.loader import Loader
from orb_optimizer.io.sources import DictSource
from orb_optimizer.models import Orb, Category, ProfileConfig, Inputs
from orb_optimizer.solvers.beam import UnifiedOptimizer
from orb_optimizer.solvers.greedy import GreedyOptimizer

router = APIRouter()


# ---- Helpers ---------------------------------------------------------------

def _dc_to_dict(obj: Any) -> Any:
    """Best-effort serializer for dataclasses and nested objects."""
    if dataclasses.is_dataclass(obj):
        return {k: _dc_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _dc_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dc_to_dict(v) for v in obj]
    # Fallback to basic types or __dict__
    if hasattr(obj, "__dict__"):
        try:
            return {k: _dc_to_dict(v) for k, v in vars(obj).items()}
        except Exception:
            pass
    return obj


def _summarize_result(result: Any) -> Dict[str, Any]:
    """
    Produce a compact view for UI:
      - total score(s) per profile
      - chosen sets per profile (if available)
      - selected orb ids/names (if available)
    This function is intentionally defensive; fills what it can.
    """
    out: Dict[str, Any] = {}
    try:
        # Common patterns you likely have on your result object:
        out["combined_score"] = getattr(result, "combined_score", None)
        out["per_profile"] = []

        per_profile = getattr(result, "per_profile", None) or []
        for pr in per_profile:
            out["per_profile"].append({
                "name": getattr(pr, "name", None),
                "score": getattr(pr, "score", None),
                "sets": getattr(pr, "sets", None),
                "orbs": getattr(pr, "orbs", None),
            })
    except Exception:
        pass
    return out


def _to_core_inputs(req: OptimizeRequest, loader: Loader) -> Inputs:
    """
    Convert API models -> your core dataclasses (Orb, Category, ProfileConfig, Inputs).
    We reuse the loader’s parsing & defaults where useful, but here the request
    already contains embedded maps, so we bypass any file I/O.
    """
    # Orbs: let loader’s parser do type normalization (level caps, value coercion, etc.)
    orbs = loader.load_orbs(DictSource([o.model_dump(by_alias=True) for o in req.orbs]))

    # Categories/Slots:
    categories = loader.load_categories(DictSource(req.slots))

    # Profiles:
    profiles: List[ProfileConfig] = []
    for p in req.profiles:
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
            )
        )

    return Inputs(
        orbs=orbs,
        categories=categories,             # List[Category] as per your core
        profiles=profiles,                 # List[ProfileConfig]
        shareable_categories=req.shareable_categories or None,
    )


# ---- Route ----------------------------------------------------------------

@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, request: Request) -> OptimizeResponse:
    """Run optimizer using embedded JSON."""
    logger = request.app.state.logger

    loader = Loader(logger)  # loader logs through same API logger
    logger.info("Received optimization request")

    try:
        inputs = _to_core_inputs(req, loader)
        logger.info(f"Loaded {len(inputs.orbs)} orbs, {len(inputs.categories)} categories, {len(inputs.profiles)} profiles")
    except Exception as e:
        logger.exception("Failed to parse request")
        raise HTTPException(status_code=400, detail=f"Invalid inputs: {e}")

    # Choose solver
    if req.algorithm == "beam":
        logger.info(f"Running beam search (width={req.beam}, topk={req.topk})")
        solver = UnifiedOptimizer(inputs=inputs, logger=logger, topk_per_category=req.topk)
        result = solver.optimize(beam_width=req.beam)
    else:
        logger.info("Running greedy optimizer")
        solver = GreedyOptimizer(inputs=inputs, logger=logger)
        result = solver.optimize()

    summary = _summarize_result(result)
    logger.info("Optimization complete")

    return OptimizeResponse(ok=True, result=OptimizeResult(summary=summary, raw=_dc_to_dict(result)))
