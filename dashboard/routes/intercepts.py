"""
dashboard/routes/intercepts.py — Weir local edition
No auth, reads straight from SQLite.
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import fetch_pending, fetch_history, patch_intercept

log = logging.getLogger("weir.intercepts")
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _parse_rows(rows: list[dict]) -> list[dict]:
    """SQLite stores dry_run as a JSON string — parse it back for templates."""
    for row in rows:
        if isinstance(row.get("dry_run"), str):
            try:
                row["dry_run"] = json.loads(row["dry_run"])
            except Exception:
                row["dry_run"] = {}
    return rows


@router.get("/")
async def root():
    return RedirectResponse("/intercepts", status_code=302)


@router.get("/intercepts")
async def intercepts_page(request: Request):
    pending = _parse_rows(await fetch_pending())
    history = _parse_rows(await fetch_history())
    return templates.TemplateResponse(
        "intercepts.html",
        {"request": request, "pending": pending, "history": history},
    )


@router.get("/intercepts/pending", response_class=HTMLResponse)
async def pending_partial(request: Request):
    pending = _parse_rows(await fetch_pending())
    return templates.TemplateResponse(
        "_pending.html", {"request": request, "pending": pending}
    )


@router.post("/intercepts/{intercept_id}/allow", response_class=HTMLResponse)
async def allow_intercept(intercept_id: str):
    await patch_intercept(intercept_id, "approved")
    return HTMLResponse("")


@router.post("/intercepts/{intercept_id}/block", response_class=HTMLResponse)
async def block_intercept(intercept_id: str):
    await patch_intercept(intercept_id, "blocked")
    return HTMLResponse("")