"""
app/api/routes/evaluation.py

GET /evaluation/results — serves whatever scripts/run_evaluation.py last
wrote (settings.eval_results_path), so the frontend dashboard can display
real Recall@K/MRR/faithfulness numbers without the frontend needing
filesystem access. This is deliberately read-only and serves a static
snapshot — the eval script is still what needs to be re-run to produce new
numbers; this endpoint doesn't trigger a run.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter()


@router.get("/evaluation/results")
async def get_evaluation_results():
    path = Path(settings.eval_results_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No evaluation results found at {path}. "
                "Run `python scripts/run_evaluation.py` first."
            ),
        )

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation results file at {path} is corrupted (invalid JSON).",
        )
