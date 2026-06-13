"""Case workflow helpers built on shared case_store."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core import case_store

logger = logging.getLogger(__name__)

TRACKED_STAGES = frozenset(
    {
        "CASE_OPENED",
        "INTAKE_REQUEST",
        "INTAKE_COMPLETE",
        "INTAKE_INCOMPLETE",
        "VERIFY_REQUEST",
        "CASE_CLEAR",
        "CASE_CAUTION",
        "CASE_ESCALATE",
        "RESOURCE_REQUEST",
        "RESOURCE_COMPLETE",
        "CASE_READY",
        "HUMAN_ALERT",
        "CASE_APPROVED",
        "CASE_REJECTED",
    }
)

TERMINAL_STAGES = frozenset({"CASE_READY", "HUMAN_ALERT", "CASE_REJECTED", "CASE_APPROVED"})
VERIFICATION_OUTCOMES = frozenset({"CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE"})


def init_case_state() -> None:
    case_store.init_store()


def is_band_message_limit_error(exc: BaseException) -> bool:
    parts: list[str] = [str(exc)]
    for attr in ("body", "text", "message"):
        val = getattr(exc, attr, None)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("text", "body", "content"):
            val = getattr(response, attr, None)
            if isinstance(val, str) and val.strip():
                parts.append(val)
    blob = " ".join(parts).lower()
    return (
        "limit_reached" in blob
        or "max_messages_per_room_count" in blob
        or "max_messages_per_room" in blob
    )


def disable_room_for_band_limit(room_id: str, exc: BaseException) -> bool:
    """Persist room disable when Band returns a message-limit error."""
    if not room_id or not is_band_message_limit_error(exc):
        return False
    case_store.disable_room(room_id, case_store.ROOM_LIMIT_REASON)
    return True


def is_room_disabled(room_id: str) -> bool:
    return case_store.is_room_disabled(room_id)


def list_disabled_rooms() -> list[dict[str, Any]]:
    return case_store.list_disabled_rooms()


def enable_room(room_id: str) -> bool:
    return case_store.enable_room(room_id)


def clear_disabled_rooms() -> int:
    return case_store.clear_disabled_rooms()


def get_case_state(case_id: str) -> dict[str, Any]:
    return case_store.get_case_state(case_id)


def completed_stages(case_id: str) -> set[str]:
    return case_store.completed_stages(case_id)


def stage_completed(case_id: str, stage: str) -> bool:
    return stage in completed_stages(case_id)


def is_terminal(case_id: str) -> bool:
    return bool(completed_stages(case_id) & TERMINAL_STAGES)


def get_verification_status(case_id: str) -> str | None:
    state = get_case_state(case_id)
    verification = state.get("verification") or {}
    if isinstance(verification, dict):
        status = verification.get("status")
        if isinstance(status, str):
            return status
    for stage in ("CASE_ESCALATE", "CASE_CAUTION", "CASE_CLEAR"):
        if stage_completed(case_id, stage):
            return stage
    return state.get("verification_status")


def record_stage(
    case_id: str,
    stage: str,
    *,
    payload: dict[str, Any] | None = None,
    room_id: str | None = None,
) -> None:
    case_store.record_stage(case_id, stage, payload=payload, room_id=room_id)
    logger.info("Recorded stage %s for case %s", stage, case_id)


def resolve_case_id(text: str, room_id: str) -> str | None:
    case_id = extract_case_id(text)
    if case_id:
        case_store.assign_room_case_id(room_id, case_id, content_fingerprint=text[:256])
        return case_id
    return case_store.get_room_case_id(room_id) or case_store.stable_case_id_for_room(
        room_id, seed_text=text[:512]
    )


def try_claim_outbound(
    case_id: str,
    stage: str,
    sender: str,
    recipient: str,
    *,
    room_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    return case_store.try_claim_idempotency(
        case_id,
        stage,
        sender,
        recipient,
        room_id=room_id,
        payload=payload,
    )


def try_claim_inbound(agent_role: str, room_id: str, message_id: str, case_id: str | None = None) -> bool:
    return case_store.try_claim_processed_message(
        agent_role,
        room_id,
        message_id,
        case_id=case_id,
    )


def extract_case_id(text: str) -> str | None:
    if not text:
        return None
    parsed = try_parse_json_payload(text)
    if parsed:
        case_id = parsed.get("case_id")
        if isinstance(case_id, str) and case_id.strip():
            return case_id.strip().upper()
    for pattern in (
        r'"case_id"\s*:\s*"([^"]+)"',
        r"Case ID:\s*([A-Z0-9-]+)",
        r"case_id[=:\s]+([A-Z0-9-]+)",
        r"\bMB-[A-F0-9]{8}\b",
        r"MEDBAND-[A-Z0-9-]+",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1 if match.lastindex else 0).upper()
    return None


def try_parse_json_payload(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        brace = cleaned.find("{")
        if brace >= 0:
            end = cleaned.rfind("}")
            if end > brace:
                cleaned = cleaned[brace : end + 1]
            else:
                return None
        else:
            return None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def detect_stage(text: str, payload: dict[str, Any] | None = None) -> str | None:
    if payload and isinstance(payload.get("status"), str):
        status = payload["status"].upper()
        if status in TRACKED_STAGES:
            return status
    upper = text.upper()
    formatted_aliases = {
        "INTAKE COMPLETE": "INTAKE_COMPLETE",
        "VERIFICATION COMPLETE": "CASE_CLEAR",
        "CASE CLEAR": "CASE_CLEAR",
        "VERIFICATION CAUTION": "CASE_CAUTION",
        "VERIFICATION ESCALATION": "CASE_ESCALATE",
        "RESOURCE COMPLETE": "RESOURCE_COMPLETE",
        "CASE READY FOR HUMAN REVIEW": "CASE_READY",
        "CASE OPENED": "CASE_OPENED",
        "HUMAN ALERT": "HUMAN_ALERT",
    }
    for label, stage in formatted_aliases.items():
        if label in upper:
            return stage
    for stage in sorted(TRACKED_STAGES, key=len, reverse=True):
        if stage in upper:
            return stage
    if "@MEDLABBYTBR/INTAKE" in upper or "INTAKE_REQUEST" in upper:
        return "INTAKE_REQUEST"
    if "@MEDLABBYTBR/VERIFICATION" in upper and ("VERIFY" in upper or "PLEASE VERIFY" in upper):
        return "VERIFY_REQUEST"
    if "@MEDLABBYTBR/RESOURCE" in upper and ("RESOURCE" in upper or "AVAILABILITY" in upper):
        return "RESOURCE_REQUEST"
    return None


def build_coordinator_workflow_context(case_id: str) -> str:
    """Structured workflow state from Postgres for Coordinator routing."""
    state = get_case_state(case_id)
    completed = sorted(state.get("completed_stages", []))
    lines = [
        "[System]: Postgres workflow state (use this for routing, not visible Band text alone)",
        f"case_id: {case_id}",
        f"completed_stages: {', '.join(completed) if completed else 'none'}",
    ]
    intake = state.get("intake")
    if isinstance(intake, dict) and intake:
        lines.append(f"intake_result: {json.dumps(intake, default=str)}")
    verification = state.get("verification")
    if isinstance(verification, dict) and verification:
        lines.append(f"verification_result: {json.dumps(verification, default=str)}")
    resource = state.get("resource")
    if isinstance(resource, dict) and resource:
        lines.append(f"resource_result: {json.dumps(resource, default=str)}")

    # Evaluate latest stage first so a completed stage never shadows a later one.
    # Once RESOURCE_COMPLETE exists, the only valid next action is CASE_READY -
    # never route back to Intake and never send PROCESS CASE again.
    if stage_completed(case_id, "RESOURCE_COMPLETE"):
        if not stage_completed(case_id, "CASE_READY"):
            lines.append(
                "required_action: Resource complete. Post exactly one CASE READY FOR HUMAN REVIEW summary to the human approver. Do NOT route back to Intake, Verification, or Resource. Do NOT send PROCESS CASE."
            )
    elif stage_completed(case_id, "CASE_ESCALATE"):
        if not stage_completed(case_id, "HUMAN_ALERT"):
            lines.append("required_action: Verification escalated. Send HUMAN_ALERT and stop.")
    elif stage_completed(case_id, "CASE_CLEAR") or stage_completed(case_id, "CASE_CAUTION"):
        if not stage_completed(case_id, "RESOURCE_REQUEST"):
            lines.append(
                "required_action: Verification complete. Send exactly one RESOURCE_REQUEST to @medlabbytbr/resource."
            )
    elif stage_completed(case_id, "INTAKE_COMPLETE") and not stage_completed(case_id, "VERIFY_REQUEST"):
        lines.append(
            "required_action: INTAKE_COMPLETE received. Send exactly one VERIFY_REQUEST to @medlabbytbr/verification with intake_result."
        )
    return "\n".join(lines)
