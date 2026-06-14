"""Band message routing guards, idempotency, and human-readable formatting."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from band.core.types import PlatformMessage

from core.case_state import (
    TRACKED_STAGES,
    detect_stage,
    extract_case_id,
    get_case_state,
    get_verification_status,
    is_terminal,
    record_stage,
    stage_completed,
    try_parse_json_payload,
)

logger = logging.getLogger(__name__)

SEND_MESSAGE_TOOLS = frozenset({"band_send_message", "thenvoi_send_message"})

AGENT_ALIASES = {
    "coordinator": {"coordinator", "medlabbytbr/coordinator", "@medlabbytbr/coordinator"},
    "intake": {"intake", "medlabbytbr/intake", "@medlabbytbr/intake"},
    "verification": {
        "verification",
        "medlabbytbr/verification",
        "@medlabbytbr/verification",
    },
    "resource": {"resource", "medlabbytbr/resource", "@medlabbytbr/resource"},
}

ROUTING_ONLY_STAGES = frozenset({"VERIFY_REQUEST", "RESOURCE_REQUEST", "INTAKE_REQUEST"})

STAGE_OWNERS = {
    "coordinator": frozenset(
        {
            "CASE_OPENED",
            "VERIFY_REQUEST",
            "RESOURCE_REQUEST",
            "CASE_READY",
            "CASE_APPROVED",
            "CASE_REJECTED",
            "HUMAN_ALERT",
        }
    ),
    "intake": frozenset({"INTAKE_COMPLETE", "INTAKE_INCOMPLETE"}),
    "verification": frozenset({"CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE"}),
    "resource": frozenset({"RESOURCE_COMPLETE"}),
}

AGENT_REPLY_STAGES = frozenset(
    {
        "INTAKE_COMPLETE",
        "CASE_CLEAR",
        "CASE_CAUTION",
        "CASE_ESCALATE",
        "RESOURCE_COMPLETE",
    }
)

# Coordinator should skip only after it has already performed the next routing step.
COORDINATOR_NEXT_STAGE: dict[str, str] = {
    "INTAKE_COMPLETE": "VERIFY_REQUEST",
    "CASE_CLEAR": "RESOURCE_REQUEST",
    "CASE_CAUTION": "RESOURCE_REQUEST",
    "CASE_ESCALATE": "HUMAN_ALERT",
    "RESOURCE_COMPLETE": "CASE_READY",
}

LEGACY_MESSAGE_MARKERS = (
    "SUMMARY FOR HUMAN REVIEW",
    "Verification passed",
    "Resource confirmed",
    "CASE READY FOR YOUR REVIEW",
    "Passing to Resource check now",
    "Passing full summary to Coordinator now",
    "Passing to Verification now",
    "Passing to Coordinator now",
    "Passing to Resource now",
)


@dataclass
class OutboundDecision:
    skip: bool = False
    reason: str = ""
    formatted_content: str | None = None
    stage: str | None = None
    case_id: str | None = None
    record_on_success: bool = True
    agent_role: str | None = None


def strip_em_dash(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def is_legacy_band_message(content: str) -> bool:
    """Block old prompt templates and --- summary messages."""
    stripped = content.strip()
    if stripped.startswith("---"):
        return True
    upper = stripped.upper()
    for marker in LEGACY_MESSAGE_MARKERS:
        if marker.upper() in upper:
            return True
    return False


def should_block_followup_summary(content: str, case_id: str | None) -> bool:
    """Block a second natural-language summary when the formatted stage already posted."""
    if not case_id:
        return False
    upper = content.upper()
    if "VERIFICATION PASSED" in upper or "VERIFICATION FAILED" in upper:
        return any(stage_completed(case_id, s) for s in ("CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE"))
    if ("RESOURCE CONFIRMED" in upper or "NOT CURRENTLY AVAILABLE" in upper) and "📦" not in content:
        return stage_completed(case_id, "RESOURCE_COMPLETE")
    if "CASE READY FOR YOUR REVIEW" in upper:
        return stage_completed(case_id, "CASE_READY")
    if "CASE READY FOR HUMAN REVIEW" in upper and stage_completed(case_id, "CASE_READY"):
        return True
    if "NO SAFETY CONCERNS FOUND" in upper or "PASSING TO RESOURCE" in upper:
        return any(stage_completed(case_id, s) for s in ("CASE_CLEAR", "CASE_CAUTION"))
    if "PASSING FULL SUMMARY TO COORDINATOR" in upper:
        return stage_completed(case_id, "RESOURCE_COMPLETE")
    return False


def _is_routing_message(content: str) -> bool:
    """Allow coordinator routing lines that are plain text without a workflow stage."""
    upper = content.upper()
    if any(
        token in upper
        for token in (
            "@MEDLABBYTBR/INTAKE",
            "@MEDLABBYTBR/VERIFICATION",
            "@MEDLABBYTBR/RESOURCE",
            "@MEDLABBYTBR/COORDINATOR",
            "NEW_CASE_FROM_WEB",
            "NEW_CASE",
            "INTAKE_REQUEST",
            "VERIFY_REQUEST",
            "RESOURCE_REQUEST",
        )
    ):
        return True
    if upper.startswith("@") and "PLEASE" in upper:
        return True
    return False


# Coordinator routing messages use a clean visible header (e.g. "VERIFY CASE")
# while the target agent handle travels in the Band mentions payload, which the
# adapter resolves to `recipient` via extract_recipient. detect_stage only sees
# the visible text, so it cannot recognize these. We infer the routing stage
# from the header + recipient pair instead, without requiring the full @handle
# to appear in the visible content.
COORDINATOR_ROUTING_HEADERS: tuple[tuple[str, str, str], ...] = (
    # (visible header, target agent role, inferred stage)
    ("VERIFY CASE", "verification", "VERIFY_REQUEST"),
    ("CHECK AVAILABILITY", "resource", "RESOURCE_REQUEST"),
)


def _recipient_targets(recipient: str | None, role: str) -> bool:
    """True when the resolved mention/recipient addresses the given agent role."""
    normalized = normalize_sender(recipient)
    if not normalized:
        return False
    aliases = {a.lower().replace("@", "") for a in AGENT_ALIASES.get(role, set())}
    return normalized in aliases


def infer_coordinator_routing_stage(
    agent_role: str | None, content: str, recipient: str | None
) -> str | None:
    """Infer a Coordinator-owned routing stage from a clean header plus the
    mention/recipient payload.

    Only the Coordinator may originate these stages, and BOTH the exact visible
    header AND a matching recipient mention must be present. That double
    requirement keeps random text from becoming a stage and stops Intake,
    Verification, or Resource from faking a Coordinator routing stage.
    """
    if (agent_role or "").lower() != "coordinator":
        return None
    upper = strip_em_dash(content or "").upper()
    for header, target_role, stage in COORDINATOR_ROUTING_HEADERS:
        if header in upper and _recipient_targets(recipient, target_role):
            return stage
    return None


def enrich_payload_from_case_state(payload: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Merge Postgres case context so Resource/Verification use intake institution and service."""
    state = get_case_state(case_id)
    intake = state.get("intake") if isinstance(state.get("intake"), dict) else {}
    opened = state.get("opened") if isinstance(state.get("opened"), dict) else {}
    merged = {**payload}
    merged.setdefault("case_id", case_id)

    for key in (
        "requester_name",
        "requested_service",
        "presenting_issue",
        "urgency",
        "prescription_code",
        "institution_name",
        "institution_id",
    ):
        val = intake.get(key) or opened.get(key)
        if val:
            merged[key] = val

    inst = intake.get("institution_name") or opened.get("institution_name")
    if inst:
        merged["institution_name"] = inst
        merged["institution"] = inst
    else:
        merged.setdefault("institution_name", merged.get("institution") or "Demo Institution")
        merged["institution"] = merged.get("institution_name") or merged.get("institution") or "Demo Institution"

    return merged


def extract_approver(content: str) -> str:
    for pattern in (
        r"Approved by[:\s]+(.+?)(?:\n|$)",
        r"Decision:\s*Approved by[:\s]+(.+?)(?:\n|$)",
        r"approval was made by[:\s]+(.+?)(?:\n|$)",
    ):
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Human reviewer"


def format_case_approved(case_id: str, payload: dict[str, Any] | None = None, approver: str = "") -> str:
    state = get_case_state(case_id)
    intake = state.get("intake") if isinstance(state.get("intake"), dict) else {}
    data = payload or {}
    patient = _pick(intake, "requester_name") or _pick(data, "requester_name", "patient_name")
    request = _pick(intake, "requested_service") or _pick(data, "requested_service")
    decision_by = approver or _pick(data, "approved_by", "approver_name") or "Human reviewer"
    return strip_em_dash(
        "\n".join(
            [
                "✅ CASE APPROVED",
                "",
                f"Case ID: {case_id}",
                "",
                "Patient:",
                patient or "Unknown",
                "",
                "Request:",
                request or "Not specified",
                "",
                "Decision:",
                f"Approved by {decision_by}",
                "",
                "Status:",
                "Closed",
                "",
                "Important:",
                "No AI approved this case. Final approval was made by the human reviewer.",
            ]
        )
    )


def detect_approval_outbound(content: str, payload: dict[str, Any] | None) -> bool:
    upper = content.upper()
    if payload and str(payload.get("status", "")).upper() == "CASE_APPROVED":
        return True
    if "CASE APPROVED" in upper:
        return True
    if "APPROVED BY" in upper and "CASE READY" not in upper:
        return True
    if re.search(r"\bAPPROVE\b", content, re.IGNORECASE) and "CASE READY" not in upper:
        if "PROCEED" in upper or "APPROVED" in upper or "CONFIRMATION" in upper:
            return True
    return False


def normalize_sender(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().lower().replace("@", "")


def is_self_sender(sender: str, agent_role: str) -> bool:
    normalized = normalize_sender(sender)
    aliases = AGENT_ALIASES.get(agent_role, {agent_role})
    return normalized in {a.lower().replace("@", "") for a in aliases}


def is_coordinator_sender(sender: str) -> bool:
    normalized = normalize_sender(sender)
    return normalized in {a.lower().replace("@", "") for a in AGENT_ALIASES["coordinator"]}


def is_agent_sender(sender: str, role: str) -> bool:
    normalized = normalize_sender(sender)
    return normalized in {a.lower().replace("@", "") for a in AGENT_ALIASES.get(role, set())}


def owns_stage(agent_role: str | None, stage: str | None) -> bool:
    if not stage:
        return True
    allowed = STAGE_OWNERS.get((agent_role or "").lower())
    if allowed is None:
        return True
    if stage not in TRACKED_STAGES:
        return True
    return stage in allowed


def _title(value: str) -> str:
    if not value:
        return "Unknown"
    return value.strip().title()


def _pick(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return default


def _case_id_lines(payload: dict[str, Any]) -> list[str]:
    case_id = _pick(payload, "case_id")
    if not case_id:
        return []
    return [f"Case ID: {case_id}", ""]


def format_case_opened(payload: dict[str, Any]) -> str:
    intake = payload.get("intake") if isinstance(payload.get("intake"), dict) else {}
    patient = _pick(payload, "requester_name", "patient_name") or _pick(intake, "requester_name", "patient_name")
    institution = _pick(payload, "institution_name") or _pick(intake, "institution_name") or "Demo Institution"
    request = _pick(payload, "requested_service", "raw_input") or _pick(intake, "requested_service")
    issue = _pick(payload, "presenting_issue") or _pick(intake, "presenting_issue")
    urgency = _title(_pick(payload, "urgency") or _pick(intake, "urgency") or "medium")
    rx = _pick(payload, "prescription_code") or _pick(intake, "prescription_code")

    lines = [
        "📋 CASE OPENED",
        "",
        *_case_id_lines(payload),
        f"Patient: {patient or 'Unknown'}",
        f"Institution: {institution}",
        f"Request: {request or 'Not specified'}",
        f"Issue: {issue or 'Not specified'}",
        f"Urgency: {urgency}",
    ]
    if rx:
        lines.append(f"Prescription Code: {rx}")
    lines.extend(
        [
            "",
            "Next Step:",
            "Intake agent will structure the request.",
        ]
    )
    return strip_em_dash("\n".join(lines))


def format_intake_complete(payload: dict[str, Any]) -> str:
    patient = _pick(payload, "requester_name")
    request = _pick(payload, "requested_service")
    issue = _pick(payload, "presenting_issue")
    urgency = _title(_pick(payload, "urgency") or "medium")
    rx = _pick(payload, "prescription_code")
    lines = [
        "📋 INTAKE COMPLETE",
        "",
        *_case_id_lines(payload),
        f"Patient: {patient or 'Unknown'}",
        f"Request: {request or 'Not specified'}",
        f"Issue: {issue or 'Not specified'}",
        f"Urgency: {urgency}",
    ]
    if rx:
        lines.append(f"Prescription Code: {rx}")
    lines.extend(
        [
            "",
            "Next Step:",
            "Coordinator will send this case to Verification.",
        ]
    )
    return strip_em_dash("\n".join(lines))


def format_verification(payload: dict[str, Any]) -> str:
    status = _pick(payload, "status", default="CASE_CLEAR").upper()
    drug = _pick(payload, "requested_service") or _pick(payload, "drug_name", "test_name")
    reason = _pick(payload, "reason", "recommendation")
    if status == "CASE_ESCALATE":
        return strip_em_dash(
            "\n".join(
                [
                    "🚨 VERIFICATION ESCALATION",
                    "",
                    *_case_id_lines(payload),
                    f"Request: {drug or 'Unknown'}",
                    f"Reason: {reason or 'Safety review required.'}",
                    "",
                    "Next Step:",
                    "Coordinator will alert a human approver.",
                ]
            )
        )
    if status == "CASE_CAUTION":
        return strip_em_dash(
            "\n".join(
                [
                    "🟡 VERIFICATION CAUTION",
                    "",
                    *_case_id_lines(payload),
                    f"Request: {drug or 'Unknown'}",
                    f"Notes: {reason or 'Proceed with caution.'}",
                    "",
                    "Next Step:",
                    "Coordinator will check resource availability.",
                ]
            )
        )
    clear_line = f"{drug or 'This request'} is cleared to proceed."
    if reason and "clear" not in reason.lower():
        clear_line = reason
    return strip_em_dash(
        "\n".join(
            [
                "✅ VERIFICATION COMPLETE",
                "",
                *_case_id_lines(payload),
                "Verification:",
                clear_line,
                "No safety concern was found.",
                "",
                "Next Step:",
                "Coordinator will check resource availability.",
            ]
        )
    )


def format_resource_complete(payload: dict[str, Any]) -> str:
    name = _pick(payload, "requested_service") or _pick(payload, "drug_name", "test_name")
    institution = _pick(payload, "institution_name") or _pick(payload, "institution")
    in_stock = payload.get("in_stock", True)
    qty = payload.get("quantity_available")
    notes = _pick(payload, "notes")
    lines = ["📦 RESOURCE COMPLETE", "", *_case_id_lines(payload)]
    lines.append(f"Request: {name or 'Unknown'}")
    if institution:
        lines.append(f"Institution: {institution}")
    if in_stock:
        if qty is not None:
            lines.append(f"Availability: In stock with {qty} units available.")
        else:
            lines.append("Availability: In stock.")
    else:
        lines.append("Availability: Not currently in stock.")
    if notes:
        lines.append(f"Notes: {notes}")
    lines.extend(["", "Next Step:", "Coordinator will prepare the case summary."])
    return strip_em_dash("\n".join(lines))


def format_case_ready(payload: dict[str, Any], case_id: str) -> str:
    state = get_case_state(case_id)
    intake = payload.get("intake") if isinstance(payload.get("intake"), dict) else state.get("intake") or {}
    verification = (
        payload.get("verification")
        if isinstance(payload.get("verification"), dict)
        else state.get("verification") or {}
    )
    resource = (
        payload.get("resource") if isinstance(payload.get("resource"), dict) else state.get("resource") or {}
    )

    patient = _pick(intake, "requester_name") or _pick(payload, "requester_name", "patient_name")
    request = _pick(intake, "requested_service") or _pick(payload, "requested_service")
    issue = _pick(intake, "presenting_issue")

    ver_status = _pick(verification, "status").upper()
    drug = _pick(verification, "drug_name") or request
    if ver_status == "CASE_CLEAR":
        verification_text = f"{drug or request or 'The request'} is cleared to proceed.\nNo safety concern was found."
    elif ver_status == "CASE_CAUTION":
        verification_text = _pick(verification, "reason") or "Proceed with caution."
    else:
        verification_text = _pick(verification, "reason") or "Verification completed."

    if resource.get("in_stock") is False:
        availability = _pick(resource, "notes") or "Not currently available."
    elif resource.get("quantity_available") is not None:
        availability = f"In stock with {resource.get('quantity_available')} units available."
    else:
        availability = _pick(resource, "notes") or "Availability confirmed."

    return strip_em_dash(
        "\n".join(
            [
                "@medband-approval-desk CASE READY FOR HUMAN REVIEW",
                "",
                "Case ID:",
                case_id,
                "",
                "Patient:",
                patient or "Unknown",
                "",
                "Issue:",
                issue or "Not specified",
                "",
                "Request:",
                request or "Not specified",
                "",
                "Verification:",
                verification_text,
                "",
                "Resource:",
                availability,
                "",
                "Human Reviewer:",
                "@medlabbytbr",
                "",
                "Decision Needed:",
                "Human reviewer should reply:",
                f"@Coordinator APPROVE {case_id}",
                "or",
                f"@Coordinator REJECT {case_id}: <reason>",
            ]
        )
    )


def format_human_alert(payload: dict[str, Any]) -> str:
    reason = _pick(payload, "reason", "message") or "Human review required."
    patient = _pick(payload, "requester_name", "patient_name")
    request = _pick(payload, "requested_service")
    institution = _pick(payload, "institution_name") or "Demo Institution"
    return strip_em_dash(
        "\n".join(
            [
                "🚨 HUMAN ALERT",
                "",
                f"Patient: {patient or 'Unknown'}",
                f"Request: {request or 'Not specified'}",
                f"Institution: {institution}",
                "",
                f"Reason: {reason}",
                "",
                "Please respond with:",
                "APPROVE WITH OVERRIDE: [justification]",
                "REJECT: [reason]",
                "ESCALATE FURTHER: [who to contact]",
            ]
        )
    )


def format_stage_message(stage: str, payload: dict[str, Any], case_id: str) -> str:
    payload = enrich_payload_from_case_state(payload or {}, case_id)
    formatters = {
        "CASE_OPENED": format_case_opened,
        "INTAKE_COMPLETE": format_intake_complete,
        "CASE_CLEAR": format_verification,
        "CASE_CAUTION": format_verification,
        "CASE_ESCALATE": format_verification,
        "RESOURCE_COMPLETE": format_resource_complete,
        "CASE_READY": lambda p: format_case_ready(p, case_id),
        "HUMAN_ALERT": format_human_alert,
        "CASE_APPROVED": lambda p: format_case_approved(
            case_id,
            p,
            _pick(p, "approved_by") or "Human reviewer",
        ),
    }
    formatter = formatters.get(stage)
    if formatter:
        return formatter(payload)
    return strip_em_dash(json.dumps(payload, indent=2, default=str))


def is_visible_json(content: str) -> bool:
    payload = try_parse_json_payload(content)
    if payload and payload.get("status"):
        return True
    stripped = content.strip()
    return stripped.startswith("{") and '"status"' in stripped


def should_skip_inbound(
    agent_role: str,
    msg: PlatformMessage,
    *,
    case_id: str | None,
) -> tuple[bool, str]:
    sender = msg.sender_name or msg.sender_type or ""

    if is_self_sender(sender, agent_role):
        logger.info(
            "SKIP inbound: same_sender agent=%s sender=%s msg_id=%s",
            agent_role,
            sender,
            msg.id,
        )
        return True, "same_sender"

    if case_id and is_terminal(case_id) and agent_role != "coordinator":
        logger.info(
            "SKIP inbound: stale_case_id agent=%s case_id=%s msg_id=%s",
            agent_role,
            case_id,
            msg.id,
        )
        return True, "stale_case_id"

    if agent_role == "intake":
        if not is_coordinator_sender(sender):
            logger.info(
                "SKIP inbound: wrong_recipient agent=intake sender=%s msg_id=%s",
                sender,
                msg.id,
            )
            return True, "wrong_recipient"
        if case_id and stage_completed(case_id, "INTAKE_COMPLETE"):
            logger.info(
                "SKIP inbound: duplicate_stage agent=intake stage=INTAKE_COMPLETE case_id=%s",
                case_id,
            )
            return True, "duplicate_stage"

    elif agent_role == "verification":
        if not is_coordinator_sender(sender):
            logger.info(
                "SKIP inbound: wrong_recipient agent=verification sender=%s msg_id=%s",
                sender,
                msg.id,
            )
            return True, "wrong_recipient"
        if is_agent_sender(sender, "resource"):
            logger.info(
                "SKIP inbound: invalid_routing agent=verification sender=resource msg_id=%s",
                msg.id,
            )
            return True, "invalid_routing"
        if case_id and any(stage_completed(case_id, s) for s in ("CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE")):
            logger.info(
                "SKIP inbound: already_processed agent=verification case_id=%s",
                case_id,
            )
            return True, "already_processed"

    elif agent_role == "resource":
        if not is_coordinator_sender(sender):
            logger.info(
                "SKIP inbound: wrong_recipient agent=resource sender=%s msg_id=%s",
                sender,
                msg.id,
            )
            return True, "wrong_recipient"
        if is_agent_sender(sender, "verification"):
            logger.info(
                "SKIP inbound: invalid_routing agent=resource sender=verification msg_id=%s",
                msg.id,
            )
            return True, "invalid_routing"
        if case_id and stage_completed(case_id, "RESOURCE_COMPLETE"):
            logger.info(
                "SKIP inbound: duplicate_stage agent=resource stage=RESOURCE_COMPLETE case_id=%s",
                case_id,
            )
            return True, "duplicate_stage"

    elif agent_role == "coordinator":
        payload = try_parse_json_payload(msg.content or "")
        incoming_stage = detect_stage(msg.content or "", payload)
        if case_id and incoming_stage in AGENT_REPLY_STAGES and not is_self_sender(sender, agent_role):
            next_stage = COORDINATOR_NEXT_STAGE.get(incoming_stage)
            if next_stage and stage_completed(case_id, next_stage):
                logger.info(
                    "SKIP inbound: duplicate_stage agent=coordinator incoming=%s next=%s case_id=%s",
                    incoming_stage,
                    next_stage,
                    case_id,
                )
                return True, "duplicate_stage"
        if case_id and stage_completed(case_id, "CASE_READY"):
            content_upper = (msg.content or "").upper()
            if not any(token in content_upper for token in ("NEW_CASE", "APPROVE", "REJECT", "MORE INFO")):
                logger.info(
                    "SKIP inbound: already_processed agent=coordinator case_id=%s",
                    case_id,
                )
                return True, "already_processed"

    return False, ""


def evaluate_outbound(
    agent_role: str,
    content: str,
    *,
    room_id: str,
    recipient: str = "room",
    case_id_hint: str | None = None,
) -> OutboundDecision:
    content = strip_em_dash(content or "")
    payload = try_parse_json_payload(content)
    stage = detect_stage(content, payload)
    if not stage:
        # The full @handle may live only in the mentions payload (resolved to
        # `recipient`), so recover Coordinator routing stages from the clean
        # header + recipient instead of skipping them as unformatted.
        stage = infer_coordinator_routing_stage(agent_role, content, recipient)
    case_id = extract_case_id(content) or (payload or {}).get("case_id") or case_id_hint
    if isinstance(case_id, str):
        case_id = case_id.upper()
    if payload and case_id and not payload.get("case_id"):
        payload = {**payload, "case_id": case_id}

    if is_legacy_band_message(content):
        logger.info(
            "SKIP outbound: legacy_template agent=%s case_id=%s room=%s",
            agent_role,
            case_id,
            room_id,
        )
        return OutboundDecision(skip=True, reason="legacy_template", case_id=case_id)

    if should_block_followup_summary(content, case_id):
        logger.info(
            "SKIP outbound: duplicate_summary agent=%s case_id=%s room=%s",
            agent_role,
            case_id,
            room_id,
        )
        return OutboundDecision(skip=True, reason="duplicate_summary", case_id=case_id)

    if (
        case_id
        and stage_completed(case_id, "CASE_READY")
        and detect_approval_outbound(content, payload)
        and not stage
    ):
        stage = "CASE_APPROVED"
        if not payload:
            payload = {"status": "CASE_APPROVED", "case_id": case_id}
        payload = enrich_payload_from_case_state(payload, case_id)
        payload["approved_by"] = extract_approver(content)

    if stage == "HUMAN_ALERT" and case_id:
        ver_status = (get_verification_status(case_id) or "").upper()
        if ver_status in {"CASE_CLEAR", "CASE_CAUTION"}:
            logger.info(
                "SKIP outbound: false HUMAN_ALERT blocked case_id=%s verification=%s",
                case_id,
                ver_status,
            )
            return OutboundDecision(skip=True, reason="false_human_alert", case_id=case_id)

    if not owns_stage(agent_role, stage):
        logger.info(
            "SKIP outbound: invalid_stage_owner agent=%s stage=%s case_id=%s",
            agent_role,
            stage,
            case_id,
        )
        return OutboundDecision(
            skip=True,
            reason="invalid_stage_owner",
            stage=stage,
            case_id=case_id,
            agent_role=agent_role,
        )

    if agent_role == "resource" and stage and "VERIFY" in stage:
        return OutboundDecision(
            skip=True,
            reason="invalid_routing",
            stage=stage,
            case_id=case_id,
            agent_role=agent_role,
        )

    if stage and case_id and stage in TRACKED_STAGES:
        # De-dupe on the PERSISTED stage only. The stage is recorded after a
        # confirmed successful send (see record_outbound_success), never here.
        # Claim-before-send previously marked a stage complete before delivery,
        # so a failed send (e.g. CASE_READY) was hidden permanently and could
        # never retry. A single Railway replica processes each room
        # sequentially, so this read check blocks duplicates on its own; on a
        # failed send nothing is recorded, so the stage simply retries.
        if stage_completed(case_id, stage):
            logger.info(
                "SKIP outbound: duplicate_stage agent=%s stage=%s case_id=%s recipient=%s room=%s",
                agent_role,
                stage,
                case_id,
                recipient,
                room_id,
            )
            return OutboundDecision(
                skip=True,
                reason="duplicate_stage",
                stage=stage,
                case_id=case_id,
                agent_role=agent_role,
            )

    if payload and stage and stage not in ROUTING_ONLY_STAGES:
        enriched = enrich_payload_from_case_state(payload, case_id or "")
        formatted = format_stage_message(stage, enriched, case_id or "")
        return OutboundDecision(
            formatted_content=formatted,
            stage=stage,
            case_id=case_id,
            agent_role=agent_role,
        )

    if is_visible_json(content) and stage not in ROUTING_ONLY_STAGES:
        if payload and stage:
            enriched = enrich_payload_from_case_state(payload, case_id or "")
            formatted = format_stage_message(stage, enriched, case_id or "")
            return OutboundDecision(
                formatted_content=formatted,
                stage=stage,
                case_id=case_id,
                agent_role=agent_role,
            )
        logger.info(
            "SKIP outbound: raw_json_blocked agent=%s room=%s",
            agent_role,
            room_id,
        )
        return OutboundDecision(skip=True, reason="raw_json_blocked", case_id=case_id)

    if not stage and content.strip() and not _is_routing_message(content):
        logger.info(
            "SKIP outbound: unformatted_message agent=%s case_id=%s room=%s preview=%s",
            agent_role,
            case_id,
            room_id,
            content[:80].replace("\n", " "),
        )
        return OutboundDecision(skip=True, reason="unformatted_message", case_id=case_id)

    return OutboundDecision(
        formatted_content=content if content else None,
        stage=stage,
        case_id=case_id,
        record_on_success=False,
        agent_role=agent_role,
    )


def extract_recipient(tool_input: dict[str, Any]) -> str:
    mentions = tool_input.get("mentions")
    if isinstance(mentions, list) and mentions:
        first = mentions[0]
        if isinstance(first, dict):
            for key in ("handle", "name", "id"):
                val = first.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip().lower()
        if isinstance(first, str):
            handle = first.lower()
            if "/" in handle:
                return handle.split("/")[-1]
            return handle.lstrip("@")
    content = tool_input.get("content", "")
    upper = content.upper()
    for handle in (
        "@MEDLABBYTBR/INTAKE",
        "@MEDLABBYTBR/VERIFICATION",
        "@MEDLABBYTBR/RESOURCE",
        "@MEDLABBYTBR/COORDINATOR",
    ):
        if handle in upper:
            return handle.split("/")[-1].lower()
    return "room"


def record_outbound_success(decision: OutboundDecision, payload: dict[str, Any] | None, room_id: str) -> None:
    """Persist the workflow stage AFTER the Band send actually succeeded.

    The adapter calls this only when execute_tool_call returns without error, so a
    failed send never records the stage and the Coordinator can retry it on the
    next turn. This replaces the old claim-before-send that permanently hid failed
    messages such as CASE_READY.
    """
    if decision is None or decision.skip:
        return
    if decision.stage and decision.case_id and decision.stage in TRACKED_STAGES:
        if not owns_stage(decision.agent_role, decision.stage):
            logger.info(
                "SKIP record outbound: invalid_stage_owner agent=%s stage=%s case_id=%s room=%s",
                decision.agent_role,
                decision.stage,
                decision.case_id,
                room_id,
            )
            return
        record_stage(decision.case_id, decision.stage, payload=payload, room_id=room_id)
