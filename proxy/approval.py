"""
proxy/approval.py — Weir local edition

POSTs intercept to the local dashboard and polls for a decision.
No API keys, no Supabase — everything goes through the dashboard's SQLite DB.
"""

import asyncio
import logging

import aiohttp

from config import ProxyConfig
from impact import generate_impact

log = logging.getLogger("weir.approval")

POLL_INTERVAL_SECONDS = 0.5
INTERCEPT_PATH = "/api/intercept"
POLL_PATH      = "/api/intercept/{id}/status"


async def _post_intercept(
    session: aiohttp.ClientSession,
    sql: str,
    query_type: str,
    dry_run_result: dict,
    impact: str,
    agent_classification: str,
    cfg: ProxyConfig,
) -> str | None:
    """POST to dashboard, return the intercept UUID or None on failure."""
    url = cfg.dashboard_url + INTERCEPT_PATH
    payload = {
        "query_type": query_type,
        "original_sql": sql,
        "impact": impact,
        "dry_run": dry_run_result,
        "agent_classification": agent_classification,
    }
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data.get("id")
            body = await resp.text()
            log.error("Dashboard returned %d: %s", resp.status, body[:200])
    except Exception as exc:
        log.error("Could not reach dashboard at %s: %s", cfg.dashboard_url, exc)
    return None


async def _poll_for_decision(
    session: aiohttp.ClientSession,
    intercept_id: str,
    cfg: ProxyConfig,
) -> str:
    """Poll dashboard every 500ms until status != pending or timeout."""
    url = cfg.dashboard_url + POLL_PATH.format(id=intercept_id)
    elapsed = 0.0
    while elapsed < cfg.approval_timeout:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status", "pending")
                    if status != "pending":
                        return status
        except Exception as exc:
            log.warning("Poll error: %s — retrying", exc)
    return "timeout"


async def _mark_timeout(
    session: aiohttp.ClientSession,
    intercept_id: str,
    cfg: ProxyConfig,
) -> None:
    url = cfg.dashboard_url + f"/api/intercept/{intercept_id}/timeout"
    try:
        async with session.post(url) as resp:
            if resp.status not in (200, 204):
                log.warning("Failed to mark timeout for %s", intercept_id)
    except Exception as exc:
        log.warning("Could not mark timeout: %s", exc)


async def request_approval(
    sql: str,
    query_type: str,
    dry_run_result: dict,
    cfg: ProxyConfig,
    agent_classification: str = "UNKNOWN",
) -> str:
    """
    Submit intercept to dashboard, wait for ALLOW or BLOCK decision.
    Fail-open: if dashboard is unreachable, allow the query through.
    """
    impact = generate_impact(
        query_type=query_type,
        tables_affected=dry_run_result.get("tables_affected", []),
        affected_count=dry_run_result.get("affected_count", -1),
        sample_rows=dry_run_result.get("sample_rows", []),
    )

    async with aiohttp.ClientSession() as session:
        intercept_id = await _post_intercept(
            session, sql, query_type, dry_run_result, impact, agent_classification, cfg
        )

        if intercept_id is None:
            log.warning("Dashboard unreachable — allowing query through (fail-open)")
            return "approved"

        log.info("Waiting for approval  id=%s  timeout=%ds", intercept_id, cfg.approval_timeout)

        decision = await _poll_for_decision(session, intercept_id, cfg)

        if decision == "timeout":
            log.warning("TIMEOUT after %ds — auto-blocking", cfg.approval_timeout)
            await _mark_timeout(session, intercept_id, cfg)

        return decision