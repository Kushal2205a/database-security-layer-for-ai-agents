"""
dashboard/routes/api.py — Weir local edition
Called by the proxy to create intercepts and poll for decisions.
"""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import insert_intercept, get_intercept, patch_intercept

log = logging.getLogger("weir.api")
router = APIRouter()


class InterceptPayload(BaseModel):
    query_type: str
    original_sql: str
    impact: str
    dry_run: dict
    agent_classification: str = "UNKNOWN"


@router.post("/api/intercept", status_code=201)
async def create_intercept(payload: InterceptPayload):
    intercept_id = str(uuid.uuid4())
    await insert_intercept({
        "id": intercept_id,
        "query_type": payload.query_type,
        "original_sql": payload.original_sql,
        "impact": payload.impact,
        "dry_run": json.dumps(payload.dry_run),
        "agent_classification": payload.agent_classification,
    })
    log.info("Intercept created: %s [%s]", intercept_id, payload.query_type)
    return {"id": intercept_id}


@router.get("/api/intercept/{intercept_id}/status")
async def get_status(intercept_id: str):
    row = await get_intercept(intercept_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": row["status"]}


@router.post("/api/intercept/{intercept_id}/timeout", status_code=204)
async def mark_timeout(intercept_id: str):
    await patch_intercept(intercept_id, "timeout")