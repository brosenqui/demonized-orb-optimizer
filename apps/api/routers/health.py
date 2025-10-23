# apps/api/routers/health.py
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
