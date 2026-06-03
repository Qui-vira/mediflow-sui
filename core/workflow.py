"""Orchestrates the 4-agent MedBand pipeline (Phase 1: direct function calls)."""
import json
import os
import uuid
from pathlib import Path

from agents import intake, resource, verification
from core.audit_log import get_log, post
from core.sector_loader import ACTIVE_SECTOR, human_role

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def run_case(raw_input: str, sector: str = None) -> dict:
    if sector:
        from core import sector_loader

        sector_loader.set_sector(sector)

    case_id = str(uuid.uuid4())[:8].upper()
    post("coordinator", "CASE_OPENED", case_id, {"raw_input": raw_input})

    intake_result = intake.run(case_id, raw_input)
    if intake_result.get("status") == "INTAKE_INCOMPLETE":
        result = {
            "case_id": case_id,
            "status": "INCOMPLETE",
            "missing": intake_result.get("missing_fields", []),
            "audit_trail": get_log(case_id),
        }
        _save_case(result)
        return result

    requested_service = intake_result.get("requested_service", "")

    verif_result = verification.run(case_id, requested_service, intake_result)

    if verif_result.get("status") == "CASE_ESCALATE":
        post(
            "coordinator",
            "HUMAN_ALERT",
            case_id,
            {
                "reason": verif_result.get("reason"),
                "action": "Workflow paused. Human review required immediately.",
            },
        )
        summary = build_summary(case_id, intake_result, verif_result, None, escalated=True)
        summary["audit_trail"] = get_log(case_id)
        _save_case(summary)
        return summary

    resource_result = resource.run(case_id, requested_service, intake_result)
    summary = build_summary(case_id, intake_result, verif_result, resource_result)
    post(
        "coordinator",
        "CASE_READY",
        case_id,
        {
            "case_id": case_id,
            "status": summary["status"],
            "human_role": summary["human_role"],
        },
    )
    summary["audit_trail"] = get_log(case_id)
    _save_case(summary)
    return summary


def build_summary(case_id, intake_r, verif_r, resource_r, escalated=False):
    return {
        "case_id": case_id,
        "sector": ACTIVE_SECTOR,
        "status": "ESCALATED" if escalated else "READY_FOR_REVIEW",
        "human_role": human_role(),
        "intake": intake_r,
        "verification": verif_r,
        "resource": resource_r,
        "audit_trail": get_log(case_id),
    }


def _save_case(summary: dict):
    CASES_DIR.mkdir(exist_ok=True)
    path = CASES_DIR / f"{summary['case_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def load_case(case_id: str) -> dict | None:
    path = CASES_DIR / f"{case_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def list_cases() -> list[str]:
    if not CASES_DIR.exists():
        return []
    return sorted(
        [p.stem for p in CASES_DIR.glob("*.json")],
        reverse=True,
    )
