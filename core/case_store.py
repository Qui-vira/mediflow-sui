"""Shared persistent storage for case workflow state and idempotency.

Backends (first match wins):
1. PostgreSQL when DATABASE_URL is set (required for multi-service Railway)
2. SQLite at MEDBAND_DATA_DIR/medband_state.db (Railway volume mount at /data)
3. Local dev fallback: repo cases/medband_state.db
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = Path("/data") if Path("/data").is_dir() else ROOT / "cases"
DATA_DIR = Path(os.environ.get("MEDBAND_DATA_DIR", str(DEFAULT_DATA_DIR)))
SQLITE_PATH = DATA_DIR / "medband_state.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

_lock = threading.Lock()
_pg_pool: Any = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _normalize_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    room_id TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_messages (
    dedupe_key TEXT PRIMARY KEY,
    agent_role TEXT NOT NULL,
    room_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    case_id TEXT,
    processed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS room_cases (
    room_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    content_fingerprint TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_stages (
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload TEXT,
    room_id TEXT,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (case_id, stage)
);
CREATE INDEX IF NOT EXISTS idx_idempotency_case ON idempotency_keys(case_id);
CREATE INDEX IF NOT EXISTS idx_processed_room ON processed_messages(room_id);
CREATE TABLE IF NOT EXISTS disabled_rooms (
    room_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    disabled_at TEXT NOT NULL
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    room_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS processed_messages (
    dedupe_key TEXT PRIMARY KEY,
    agent_role TEXT NOT NULL,
    room_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    case_id TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS room_cases (
    room_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    content_fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS case_stages (
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload JSONB,
    room_id TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, stage)
);
CREATE INDEX IF NOT EXISTS idx_idempotency_case ON idempotency_keys(case_id);
CREATE INDEX IF NOT EXISTS idx_processed_room ON processed_messages(room_id);
CREATE TABLE IF NOT EXISTS disabled_rooms (
    room_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    disabled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def backend_name() -> str:
    if DATABASE_URL:
        return "postgresql"
    return f"sqlite:{SQLITE_PATH}"


def _ensure_sqlite() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.executescript(SCHEMA_SQLITE)
        conn.commit()


def _get_pg_connection():
    global _pg_pool
    if _pg_pool is None:
        import psycopg

        _pg_pool = psycopg.connect(_normalize_pg_url(DATABASE_URL), autocommit=True)
        with _pg_pool.cursor() as cur:
            cur.execute(SCHEMA_POSTGRES)
    return _pg_pool


@contextmanager
def _connection() -> Iterator[Any]:
    if DATABASE_URL:
        yield _get_pg_connection()
        return
    _ensure_sqlite()
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_store() -> None:
    with _lock:
        if DATABASE_URL:
            _get_pg_connection()
            message = "Case store initialized: PostgreSQL"
            logger.info(message)
            print(message, flush=True)
        else:
            _ensure_sqlite()
            message = f"Case store initialized: SQLite at {SQLITE_PATH}"
            logger.info(message)
            print(message, flush=True)


def make_idempotency_key(
    case_id: str,
    stage: str,
    sender: str,
    recipient: str,
) -> str:
    parts = [
        case_id.upper().strip(),
        stage.upper().strip(),
        sender.lower().strip(),
        recipient.lower().strip(),
    ]
    return "|".join(parts)


def try_claim_idempotency(
    case_id: str,
    stage: str,
    sender: str,
    recipient: str,
    *,
    room_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    """Return True if this is the first claim; False if duplicate."""
    if not case_id or not stage:
        return True
    key = make_idempotency_key(case_id, stage, sender, recipient)
    payload_json = _json_dumps(payload) if payload else None
    now = _utcnow()
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO idempotency_keys
                            (idempotency_key, case_id, stage, sender, recipient, room_id, payload, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (idempotency_key) DO NOTHING
                        """,
                        (key, case_id.upper(), stage, sender, recipient, room_id, payload_json, now),
                    )
                    return cur.rowcount == 1
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO idempotency_keys
                    (idempotency_key, case_id, stage, sender, recipient, room_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, case_id.upper(), stage, sender, recipient, room_id, payload_json, now),
            )
            return cur.rowcount == 1


def idempotency_exists(
    case_id: str,
    stage: str,
    sender: str,
    recipient: str,
) -> bool:
    key = make_idempotency_key(case_id, stage, sender, recipient)
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM idempotency_keys WHERE idempotency_key = %s",
                    (key,),
                )
                return cur.fetchone() is not None
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM idempotency_keys WHERE idempotency_key = ?",
            (key,),
        )
        return cur.fetchone() is not None


def try_claim_processed_message(
    agent_role: str,
    room_id: str,
    message_id: str,
    *,
    case_id: str | None = None,
) -> bool:
    """Return True if agent should process message; False if already handled."""
    dedupe_key = f"{agent_role}|{room_id}|{message_id}"
    now = _utcnow()
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO processed_messages
                            (dedupe_key, agent_role, room_id, message_id, case_id, processed_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (dedupe_key) DO NOTHING
                        """,
                        (dedupe_key, agent_role, room_id, message_id, case_id, now),
                    )
                    return cur.rowcount == 1
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO processed_messages
                    (dedupe_key, agent_role, room_id, message_id, case_id, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (dedupe_key, agent_role, room_id, message_id, case_id, now),
            )
            return cur.rowcount == 1


def get_room_case_id(room_id: str) -> str | None:
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT case_id FROM room_cases WHERE room_id = %s",
                    (room_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        cur = conn.cursor()
        cur.execute("SELECT case_id FROM room_cases WHERE room_id = ?", (room_id,))
        row = cur.fetchone()
        return row[0] if row else None


def assign_room_case_id(room_id: str, case_id: str, content_fingerprint: str = "") -> str:
    case_id = case_id.upper()
    now = _utcnow()
    with _lock:
        existing = get_room_case_id(room_id)
        if existing:
            return existing
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO room_cases (room_id, case_id, content_fingerprint, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (room_id) DO NOTHING
                        """,
                        (room_id, case_id, content_fingerprint, now),
                    )
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT OR IGNORE INTO room_cases
                        (room_id, case_id, content_fingerprint, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (room_id, case_id, content_fingerprint, now),
                )
        return get_room_case_id(room_id) or case_id


def stable_case_id_for_room(room_id: str, seed_text: str = "") -> str:
    existing = get_room_case_id(room_id)
    if existing:
        return existing
    digest = hashlib.sha256(f"{room_id}:{seed_text}".encode()).hexdigest()[:8].upper()
    case_id = f"MB-{digest}"
    return assign_room_case_id(room_id, case_id, content_fingerprint=seed_text[:256])


def record_stage(
    case_id: str,
    stage: str,
    *,
    payload: dict[str, Any] | None = None,
    room_id: str | None = None,
) -> None:
    if not case_id or not stage:
        return
    payload_json = _json_dumps(payload) if payload else None
    now = _utcnow()
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO case_stages (case_id, stage, payload, room_id, recorded_at)
                        VALUES (%s, %s, %s::jsonb, %s, %s)
                        ON CONFLICT (case_id, stage) DO NOTHING
                        """,
                        (case_id.upper(), stage, payload_json, room_id, now),
                    )
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT OR IGNORE INTO case_stages
                        (case_id, stage, payload, room_id, recorded_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (case_id.upper(), stage, payload_json, room_id, now),
                )


def completed_stages(case_id: str) -> set[str]:
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT stage FROM case_stages WHERE case_id = %s",
                    (case_id.upper(),),
                )
                return {row[0] for row in cur.fetchall()}
        cur = conn.cursor()
        cur.execute(
            "SELECT stage FROM case_stages WHERE case_id = ?",
            (case_id.upper(),),
        )
        return {row[0] for row in cur.fetchall()}


def get_stage_payload(case_id: str, stage: str) -> dict[str, Any] | None:
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload FROM case_stages WHERE case_id = %s AND stage = %s",
                    (case_id.upper(), stage),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return None
                return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM case_stages WHERE case_id = ? AND stage = ?",
            (case_id.upper(), stage),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])


ROOM_LIMIT_REASON = "max_messages_per_room_count"


def disable_room(room_id: str, reason: str = ROOM_LIMIT_REASON) -> None:
    if not room_id:
        return
    now = _utcnow()
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO disabled_rooms (room_id, reason, disabled_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (room_id) DO UPDATE
                            SET reason = EXCLUDED.reason, disabled_at = EXCLUDED.disabled_at
                        """,
                        (room_id, reason, now),
                    )
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO disabled_rooms (room_id, reason, disabled_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT (room_id) DO UPDATE SET
                        reason = excluded.reason,
                        disabled_at = excluded.disabled_at
                    """,
                    (room_id, reason, now),
                )


def is_room_disabled(room_id: str) -> bool:
    if not room_id:
        return False
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM disabled_rooms WHERE room_id = %s",
                    (room_id,),
                )
                return cur.fetchone() is not None
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM disabled_rooms WHERE room_id = ?", (room_id,))
        return cur.fetchone() is not None


def list_disabled_rooms() -> list[dict[str, Any]]:
    with _connection() as conn:
        if DATABASE_URL:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT room_id, reason, disabled_at FROM disabled_rooms ORDER BY disabled_at DESC"
                )
                return [
                    {"room_id": row[0], "reason": row[1], "disabled_at": str(row[2])}
                    for row in cur.fetchall()
                ]
        cur = conn.cursor()
        cur.execute(
            "SELECT room_id, reason, disabled_at FROM disabled_rooms ORDER BY disabled_at DESC"
        )
        return [
            {"room_id": row[0], "reason": row[1], "disabled_at": row[2]}
            for row in cur.fetchall()
        ]


def enable_room(room_id: str) -> bool:
    """Remove a room from the disabled list. Returns True if a row was deleted."""
    if not room_id:
        return False
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM disabled_rooms WHERE room_id = %s", (room_id,))
                    return cur.rowcount > 0
            cur = conn.cursor()
            cur.execute("DELETE FROM disabled_rooms WHERE room_id = ?", (room_id,))
            return cur.rowcount > 0


def clear_disabled_rooms() -> int:
    """Remove all disabled rooms. Returns count deleted."""
    with _lock:
        with _connection() as conn:
            if DATABASE_URL:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM disabled_rooms")
                    return cur.rowcount
            cur = conn.cursor()
            cur.execute("DELETE FROM disabled_rooms")
            return cur.rowcount


def get_case_state(case_id: str) -> dict[str, Any]:
    stages = completed_stages(case_id)
    state: dict[str, Any] = {"case_id": case_id.upper(), "completed_stages": sorted(stages)}
    for stage in stages:
        payload = get_stage_payload(case_id, stage)
        if not payload:
            continue
        if stage in {"INTAKE_COMPLETE", "INTAKE_INCOMPLETE"}:
            state["intake"] = payload
        elif stage in {"CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE"}:
            state["verification"] = payload
            state["verification_status"] = stage
        elif stage == "RESOURCE_COMPLETE":
            state["resource"] = payload
        elif stage == "CASE_OPENED":
            state["opened"] = payload
        elif stage == "CASE_READY":
            state["summary"] = payload
            state["status"] = "CASE_READY"
    return state
