"""
dashboard/database.py — Weir local edition
SQLite-backed storage. Zero config — db file created automatically.
"""

import os
import aiosqlite

DB_PATH = os.getenv("WEIR_DB_PATH", "weir.db")


async def init_db() -> None:
    """Create tables if they don't exist. Called once on startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS intercepts (
                id                 TEXT PRIMARY KEY,
                query_type         TEXT NOT NULL,
                original_sql       TEXT NOT NULL,
                impact             TEXT NOT NULL,
                dry_run            TEXT NOT NULL,
                agent_classification TEXT NOT NULL DEFAULT 'UNKNOWN',
                status             TEXT NOT NULL DEFAULT 'pending',
                created_at         TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at        TEXT
            )
        """)
        await db.commit()


async def insert_intercept(row: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO intercepts
               (id, query_type, original_sql, impact, dry_run, agent_classification, status)
               VALUES (:id, :query_type, :original_sql, :impact, :dry_run,
                       :agent_classification, 'pending')""",
            row,
        )
        await db.commit()


async def fetch_pending() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM intercepts WHERE status='pending' ORDER BY created_at ASC"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def fetch_history(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM intercepts WHERE status!='pending' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_intercept(intercept_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM intercepts WHERE id=?", (intercept_id,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def patch_intercept(intercept_id: str, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE intercepts SET status=?, resolved_at=datetime('now') WHERE id=?",
            (status, intercept_id),
        )
        await db.commit()