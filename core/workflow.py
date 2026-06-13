"""Orchestrates the 4-agent MedBand pipeline (Phase 1: direct function calls)."""
import json
import uuid
from pathlib import Path

from agents import intake, resource, verification
from core.audit_log import clear, get_log, post
from core.reports import build_patient_report
from core.sector_loader import (
    band_room_name,
    get_active_sector,
    get_institution,
    human_role,
    set_active_sector,
)

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def run_case(
    raw_input: str,
    sector: str = "pharmacy",
    institution_id: str | None = None,
) -> dict:
    summary = None
    for event in run_case_stream(raw_input, sector=sector, institution_id=institution_id):
        if event.get("type") == "complete":
            summary = event["case"]
    return summary or {"status": "ERROR", "error": "Workflow did not complete"}


def run_case_stream(
    raw_input: str,
    sector: str = "pharmacy",
    institution_id: str | None = None,
):
    """Yield NDJSON events as each agent completes (for live UI updates)."""
    set_active_sector(sector)
    institution = get_institution(sector, institution_id) if institution_id else None

    clear()
    case_id = str(uuid.uuid4())[:8].upper()
    room = band_room_name(case_id, sector=sector, institution_id=institution_id)

    opened_payload = {
        "raw_input": raw_input,
        "sector": sector,
        "band_room": room,
    }
    if institution:
        opened_payload["institution"] = {
            "id": institution["id"],
            "name": institution["name"],
            "location": institution.get("location"),
        }
        opened_payload["institution_id"] = institution["id"]
        opened_payload["institution_name"] = institution["name"]
        opened_payload["institution_location"] = institution.get("location")
        opened_payload["human_role"] = human_role(sector)

    post("coordinator", "CASE_OPENED", case_id, opened_payload)
    yield _event("agent_active", agent="coordinator", message="Opening case...", case_id=case_id)
    yield _event("agent_done", agent="coordinator", status="CASE_OPENED", case_id=case_id)

    yield _event("agent_active", agent="intake", message="Extracting patient details...", case_id=case_id)
    intake_result = intake.run(case_id, raw_input, institution=institution)
    yield _event("agent_done", agent="intake", status=intake_result.get("status"), case_id=case_id, data=intake_result)

    if intake_result.get("status") == "INTAKE_INCOMPLETE":
        result = {
            "case_id": case_id,
            "sector": get_active_sector(),
            "band_room": room,
            "institution": institution,
            "institution_id": institution_id,
            "status": "INCOMPLETE",
            "missing": intake_result.get("missing_fields", []),
            "intake": intake_result,
            "audit_trail": get_log(case_id),
        }
        _save_case(result)
        yield _event("complete", case=result, report=build_patient_report(result))
        return

    requested_service = intake_result.get("requested_service", "")

    yield _event("agent_active", agent="verification", message="Checking registry and risk rules...", case_id=case_id)
    verif_result = verification.run(case_id, requested_service, intake_result)
    yield _event("agent_done", agent="verification", status=verif_result.get("status"), case_id=case_id, data=verif_result)

    if verif_result.get("status") == "CASE_ESCALATE":
        post(
            "coordinator",
            "HUMAN_ALERT",
            case_id,
            {
                "reason": verif_result.get("reason"),
                "action": "Workflow paused. Human review required immediately.",
                "band_room": room,
            },
        )
        yield _event("agent_done", agent="coordinator", status="HUMAN_ALERT", case_id=case_id)
        summary = build_summary(
            case_id, intake_result, verif_result, None, escalated=True,
            institution=institution, institution_id=institution_id, band_room=room,
        )
        summary["audit_trail"] = get_log(case_id)
        _save_case(summary)
        yield _event("complete", case=summary, report=build_patient_report(summary))
        return

    yield _event("agent_active", agent="resource", message="Checking availability and stock...", case_id=case_id)
    resource_result = resource.run(case_id, requested_service, intake_result)
    yield _event("agent_done", agent="resource", status=resource_result.get("status"), case_id=case_id, data=resource_result)

    summary = build_summary(
        case_id, intake_result, verif_result, resource_result,
        institution=institution, institution_id=institution_id, band_room=room,
    )
    post(
        "coordinator",
        "CASE_READY",
        case_id,
        {
            "case_id": case_id,
            "status": summary["status"],
            "human_role": summary["human_role"],
            "band_room": room,
            "institution_name": institution.get("name") if institution else None,
        },
    )
    yield _event("agent_done", agent="coordinator", status="CASE_READY", case_id=case_id)
    summary["audit_trail"] = get_log(case_id)
    _save_case(summary)
    yield _event("complete", case=summary, report=build_patient_report(summary))


def _event(event_type: str, **payload):
    return {"type": event_type, **payload}


def build_summary(
    case_id,
    intake_r,
    verif_r,
    resource_r,
    escalated=False,
    institution=None,
    institution_id=None,
    band_room=None,
):
    return {
        "case_id": case_id,
        "sector": get_active_sector(),
        "band_room": band_room,
        "institution": institution,
        "institution_id": institution_id,
        "status": "ESCALATED" if escalated else "READY_FOR_REVIEW",
        "human_role": human_role(),
        "intake": intake_r,
        "verification": verif_r,
        "resource": resource_r,
        "audit_trail": get_log(case_id),
    }


def save_decision(case_id: str, decision: dict) -> dict | None:
    case = load_case(case_id)
    if not case:
        return None
    case["decision"] = decision
    case["patient_report"] = build_patient_report(case)
    _save_case(case)
    post("human", decision.get("decision", "DECISION"), case_id, decision)
    return case


def _save_case(summary: dict):
    CASES_DIR.mkdir(exist_ok=True)
    path = CASES_DIR / f"{summary['case_id']}.json"
    if path.exists():
        existing = json.load(open(path, encoding="utf-8"))
        if existing.get("decision") and "decision" not in summary:
            summary["decision"] = existing["decision"]
    summary.setdefault("patient_report", build_patient_report(summary))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def load_case(case_id: str) -> dict | None:
    path = CASES_DIR / f"{case_id}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            case = json.load(f)
        case.setdefault("patient_report", build_patient_report(case))
        return case
    return None


def list_cases() -> list[str]:
    if not CASES_DIR.exists():
        return []
    return sorted([p.stem for p in CASES_DIR.glob("*.json")], reverse=True)
