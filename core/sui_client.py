"""Sui on-chain client for the ``mediflow_sui::case_router`` Move contract.

This is the SUI_MODE bridge that ``core/workflow.py`` uses to route case stage
completions onto the Sui blockchain instead of (only) an in-memory Band-style
audit log. Each workflow stage maps to one Move entry point:

    open_case            -> open_case(case_id, sector, case_blob)
    intake stage         -> record_intake(case, walrus_blob_id)
    verification stage   -> record_verification(case, outcome, walrus_blob_id)
    resource stage       -> record_resource(case, walrus_blob_id)
    human approval       -> approve_case(case, reason)
    human rejection      -> reject_case(case, reason)

Transactions are submitted with the installed Sui CLI (``sui client call``),
which uses the active address/keypair and the network selected by ``SUI_RPC_URL``
/ the CLI's active env. The bulky payloads themselves live in Walrus
(see ``core/walrus_client.py``); only the Walrus blob id reference is written
on-chain.

Configuration (see ``.env.sui.example``):
    SUI_MODE         enables the Sui path (read in workflow.py)
    SUI_RPC_URL      full node RPC endpoint
    SUI_PRIVATE_KEY  signing key for the agent/coordinator address
    SUI_PACKAGE_ID   published package id of mediflow_sui
    SUI_BIN          optional path to the sui binary (default: "sui" on PATH)
    SUI_GAS_BUDGET   optional gas budget (default: 100000000)

When ``SUI_PACKAGE_ID`` is not set the client runs in a clearly-labelled
"dry run" mode: it logs the intended Move call and returns a synthetic digest /
object id instead of submitting, so development and tests never require a live
chain or a funded key.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# In-memory record of every Move call attempted this process (for inspection
# and verification). Cleared via clear().
_submitted: list[dict[str, Any]] = []

MODULE = "case_router"


class SuiError(RuntimeError):
    """Raised when a Sui transaction submission fails."""


def _sui_bin() -> str:
    return os.getenv("SUI_BIN", "sui")


def _gas_budget() -> str:
    return os.getenv("SUI_GAS_BUDGET", "100000000")


def is_configured() -> bool:
    """True when a published package id is set; False => dry-run mode."""
    return bool(os.getenv("SUI_PACKAGE_ID", "").strip())


def _synthetic_digest(function: str, args: list[Any]) -> str:
    seed = function + "|" + json.dumps(args, default=str)
    return "dryrun-tx-" + hashlib.sha256(seed.encode()).hexdigest()[:24]


def _synthetic_object_id(case_id: str) -> str:
    return "0xdryrun" + hashlib.sha256(case_id.encode()).hexdigest()[:32]


def _dry_run(function: str, args: list[Any], *, object_id: str | None = None) -> dict[str, Any]:
    rec = {
        "function": function,
        "args": args,
        "object_id": object_id,
        "digest": _synthetic_digest(function, args),
        "dry_run": True,
    }
    _submitted.append(rec)
    logger.info("[Sui] dry-run %s args=%s -> %s", function, args, rec["digest"])
    return rec


def _extract_created_case_object_id(tx_json: dict[str, Any]) -> str | None:
    """Find the created Case shared object id in a `sui client call --json` result."""
    for change in tx_json.get("objectChanges", []) or []:
        if (
            change.get("type") == "created"
            and "case_router::Case" in str(change.get("objectType", ""))
        ):
            return change.get("objectId")
    return None


def _call(function: str, args: list[Any]) -> dict[str, Any]:
    """Submit a Move call via the Sui CLI. Args are passed as strings.

    The shared ``Case`` object id (when present) must be the FIRST element of
    ``args``; the CLI resolves shared objects automatically.
    """
    package = os.getenv("SUI_PACKAGE_ID", "").strip()
    cmd = [
        _sui_bin(),
        "client",
        "call",
        "--package",
        package,
        "--module",
        MODULE,
        "--function",
        function,
        "--gas-budget",
        _gas_budget(),
        "--json",
    ]
    if args:
        cmd.append("--args")
        cmd.extend(str(a) for a in args)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as exc:  # noqa: BLE001
        raise SuiError(f"Failed to invoke sui CLI for {function}: {exc}") from exc

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise SuiError(f"sui client call {function} failed: {detail}")

    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {"raw_stdout": proc.stdout}

    rec = {
        "function": function,
        "args": args,
        "digest": out.get("digest"),
        "dry_run": False,
        "raw": out,
    }
    _submitted.append(rec)
    logger.info("[Sui] submitted %s -> digest=%s", function, rec["digest"])
    return rec


# === Move entry points ===

def open_case(case_id: str, sector: str, case_blob: str) -> dict[str, Any]:
    """Call open_case; returns a dict including the created Case object_id."""
    args = [case_id, sector, case_blob]
    if not is_configured():
        return _dry_run("open_case", args, object_id=_synthetic_object_id(case_id))
    rec = _call("open_case", args)
    rec["object_id"] = _extract_created_case_object_id(rec.get("raw", {}))
    return rec


def record_intake(case_object_id: str, walrus_blob_id: str) -> dict[str, Any]:
    args = [case_object_id, walrus_blob_id]
    if not is_configured():
        return _dry_run("record_intake", args, object_id=case_object_id)
    return _call("record_intake", args)


def record_verification(case_object_id: str, outcome: str, walrus_blob_id: str) -> dict[str, Any]:
    args = [case_object_id, outcome, walrus_blob_id]
    if not is_configured():
        return _dry_run("record_verification", args, object_id=case_object_id)
    return _call("record_verification", args)


def record_resource(case_object_id: str, walrus_blob_id: str) -> dict[str, Any]:
    args = [case_object_id, walrus_blob_id]
    if not is_configured():
        return _dry_run("record_resource", args, object_id=case_object_id)
    return _call("record_resource", args)


def approve_case(case_object_id: str, reason: str) -> dict[str, Any]:
    args = [case_object_id, reason or ""]
    if not is_configured():
        return _dry_run("approve_case", args, object_id=case_object_id)
    return _call("approve_case", args)


def reject_case(case_object_id: str, reason: str) -> dict[str, Any]:
    args = [case_object_id, reason or ""]
    if not is_configured():
        return _dry_run("reject_case", args, object_id=case_object_id)
    return _call("reject_case", args)


# === Inspection helpers ===

def submitted() -> list[dict[str, Any]]:
    return list(_submitted)


def clear() -> None:
    _submitted.clear()
