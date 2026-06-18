"""Walrus decentralized storage client (Sui edition).

This is the SUI_MODE replacement for ``core/audit_log.py``. The original
``audit_log.py`` keeps the case audit trail in an in-memory Python list
("mock Band room"); this module instead persists case records and per-stage
agent payloads to Walrus decentralized storage over the Walrus HTTP API and
returns the resulting blob id for each write. Those blob ids are what the Sui
``case_router`` Move contract stores on-chain (see ``sui/sources/case_router.move``).

``core/audit_log.py`` is intentionally NOT modified. This module mirrors its
public surface (``post`` / ``get_log`` / ``clear``) so the Sui execution path
can swap one for the other, and adds blob-oriented helpers
(``store_case_record`` / ``store_stage_payload`` / ``read_blob``).

Walrus HTTP API used:
  * store (publisher):   PUT  {publisher}/v1/blobs?epochs={n}   body = raw bytes
  * read  (aggregator):  GET  {aggregator}/v1/blobs/{blob_id}

Configuration (see ``.env.sui.example``):
  * WALRUS_API_URL        base URL used for both publisher and aggregator
  * WALRUS_API_KEY        optional bearer token for hosted Walrus gateways
  * WALRUS_PUBLISHER_URL  optional override (defaults to WALRUS_API_URL)
  * WALRUS_AGGREGATOR_URL optional override (defaults to WALRUS_API_URL)
  * WALRUS_EPOCHS         optional storage duration in epochs (default 5)

When no Walrus endpoint is configured the client runs in a clearly-labelled
"dry run" mode: it returns a deterministic ``dryrun-<sha256>`` blob id instead
of failing, so local development and the non-Sui path never break.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# In-memory index of everything written this process (drop-in for audit_log._log).
# Each entry mirrors audit_log.post() and adds the Walrus blob id.
_log: list[dict[str, Any]] = []


class WalrusError(RuntimeError):
    """Raised when a Walrus HTTP store/read fails."""


def _publisher_url() -> str:
    return (
        os.getenv("WALRUS_PUBLISHER_URL")
        or os.getenv("WALRUS_API_URL", "")
    ).rstrip("/")


def _aggregator_url() -> str:
    return (
        os.getenv("WALRUS_AGGREGATOR_URL")
        or os.getenv("WALRUS_API_URL", "")
    ).rstrip("/")


def _epochs() -> int:
    try:
        return int(os.getenv("WALRUS_EPOCHS", "5"))
    except ValueError:
        return 5


def _auth_headers() -> dict[str, str]:
    key = os.getenv("WALRUS_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def is_configured() -> bool:
    """True when a Walrus publisher endpoint is set; False => dry-run mode."""
    return bool(_publisher_url())


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_bytes(content: Any) -> bytes:
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    return json.dumps(content, default=str, ensure_ascii=False).encode("utf-8")


def _dryrun_blob_id(payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()[:32]
    return f"dryrun-{digest}"


def _extract_blob_id(response_json: dict[str, Any]) -> str:
    """Pull the blobId out of a Walrus publisher PUT response.

    Walrus returns either ``newlyCreated`` (first time the blob is stored) or
    ``alreadyCertified`` (the blob already exists on the network).
    """
    newly = response_json.get("newlyCreated")
    if isinstance(newly, dict):
        blob_object = newly.get("blobObject", {})
        blob_id = blob_object.get("blobId") or newly.get("blobId")
        if blob_id:
            return blob_id
    already = response_json.get("alreadyCertified")
    if isinstance(already, dict) and already.get("blobId"):
        return already["blobId"]
    # Some gateways return a flat {"blobId": "..."}.
    if response_json.get("blobId"):
        return response_json["blobId"]
    raise WalrusError(f"Could not find blobId in Walrus response: {response_json}")


def store_blob(content: Any, *, epochs: int | None = None) -> str:
    """Store bytes/str/JSON-able content in Walrus, returning the blob id.

    Falls back to a deterministic dry-run id when Walrus is not configured.
    """
    payload = _to_bytes(content)

    if not is_configured():
        blob_id = _dryrun_blob_id(payload)
        logger.info("[Walrus] dry-run (WALRUS_API_URL unset) -> %s", blob_id)
        return blob_id

    import httpx  # lazy import so this module imports even without httpx

    url = f"{_publisher_url()}/v1/blobs"
    params = {"epochs": epochs if epochs is not None else _epochs()}
    try:
        resp = httpx.put(
            url,
            params=params,
            content=payload,
            headers={"Content-Type": "application/octet-stream", **_auth_headers()},
            timeout=60.0,
        )
        resp.raise_for_status()
        blob_id = _extract_blob_id(resp.json())
    except Exception as exc:  # noqa: BLE001 - surface any transport/HTTP failure
        raise WalrusError(f"Walrus store failed ({url}): {exc}") from exc

    logger.info("[Walrus] stored %d bytes -> blob_id=%s", len(payload), blob_id)
    return blob_id


def read_blob(blob_id: str) -> bytes:
    """Read raw bytes for a blob id from the Walrus aggregator."""
    if blob_id.startswith("dryrun-") or not is_configured():
        raise WalrusError(f"Blob {blob_id} is not retrievable (dry-run / unconfigured).")

    import httpx

    url = f"{_aggregator_url()}/v1/blobs/{blob_id}"
    try:
        resp = httpx.get(url, headers=_auth_headers(), timeout=60.0)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:  # noqa: BLE001
        raise WalrusError(f"Walrus read failed ({url}): {exc}") from exc


def read_json(blob_id: str) -> Any:
    """Read a blob and parse it as JSON."""
    return json.loads(read_blob(blob_id).decode("utf-8"))


def store_case_record(case: dict[str, Any]) -> str:
    """Persist a full case record to Walrus. Returns the blob id."""
    record = {"type": "case_record", "stored_at": _utcnow(), **case}
    blob_id = store_blob(record)
    _log.append(
        {
            "kind": "case_record",
            "case_id": case.get("case_id"),
            "blob_id": blob_id,
            "timestamp": record["stored_at"],
        }
    )
    return blob_id


def store_stage_payload(case_id: str, stage: str, payload: dict[str, Any]) -> str:
    """Persist a single agent/coordinator stage payload to Walrus.

    Returns the Walrus blob id, which the caller passes to the on-chain
    ``record_*`` Move function.
    """
    record = {
        "type": "stage_payload",
        "case_id": case_id,
        "stage": stage,
        "stored_at": _utcnow(),
        "payload": payload,
    }
    blob_id = store_blob(record)
    _log.append(
        {
            "kind": "stage_payload",
            "case_id": case_id,
            "stage": stage,
            "blob_id": blob_id,
            "timestamp": record["stored_at"],
        }
    )
    return blob_id


def post(agent: str, status: str, case_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Drop-in replacement for ``core.audit_log.post`` that persists to Walrus.

    Same call signature and return shape as audit_log.post, with an added
    ``blob_id`` field pointing at the Walrus-stored payload.
    """
    blob_id = store_stage_payload(case_id, status, {"agent": agent, **data})
    entry = {
        "agent": agent,
        "status": status,
        "case_id": case_id,
        "timestamp": _utcnow(),
        "blob_id": blob_id,
        "data": data,
    }
    _log.append(entry)
    print(f"[WALRUS] {agent} -> {status} | case: {case_id} | blob: {blob_id}")
    return entry


def get_log(case_id: str | None = None) -> list[dict[str, Any]]:
    """Return audit entries written this process (optionally filtered by case)."""
    entries = [e for e in _log if "status" in e]
    if case_id:
        return [e for e in entries if e.get("case_id") == case_id]
    return list(entries)


def blobs_for_case(case_id: str) -> list[dict[str, Any]]:
    """Return every Walrus blob reference recorded for a case this process."""
    return [e for e in _log if e.get("case_id") == case_id and e.get("blob_id")]


def clear() -> None:
    """Clear the in-memory index (mirrors audit_log.clear; does not delete blobs)."""
    _log.clear()
