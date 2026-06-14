"""Tests for Band message guards and formatting."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from band.core.types import PlatformMessage

from core.band_messaging import (
    OutboundDecision,
    evaluate_outbound,
    extract_recipient,
    format_case_approved,
    format_case_opened,
    is_legacy_band_message,
    is_visible_json,
    record_outbound_success,
    should_skip_inbound,
    strip_em_dash,
)
from core.case_state import init_case_state, record_stage, stage_completed


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("MEDBAND_DATA_DIR", str(tmp_path))
    import core.case_store as store

    store.DATA_DIR = tmp_path
    store.SQLITE_PATH = tmp_path / "medband_state.db"
    store._pg_pool = None
    init_case_state()


def _msg(content: str, sender: str = "Coordinator") -> PlatformMessage:
    return PlatformMessage(
        id="m1",
        room_id="room1",
        content=content,
        sender_id="s1",
        sender_type="Agent",
        sender_name=sender,
        message_type="text",
        metadata={},
        created_at=datetime.now(timezone.utc),
    )


def test_strip_em_dash():
    assert strip_em_dash("hello — world") == "hello - world"


def test_format_case_opened():
    text = format_case_opened(
        {
            "requester_name": "Ada Okonkwo",
            "institution_name": "Demo Institution",
            "requested_service": "Amoxicillin 500mg",
            "presenting_issue": "Throat infection",
            "urgency": "medium",
            "prescription_code": "TBR-DOC-0042",
        }
    )
    assert "📋 CASE OPENED" in text
    assert "Ada Okonkwo" in text
    assert "—" not in text


def test_duplicate_stage_blocked():
    case_id = "TEST1234"
    record_stage(case_id, "CASE_OPENED", payload={"status": "CASE_OPENED", "case_id": case_id})
    raw = json.dumps({"status": "CASE_OPENED", "case_id": case_id})
    decision = evaluate_outbound("coordinator", raw, room_id="room1")
    assert decision.skip is True
    assert decision.reason == "duplicate_stage"


def test_false_human_alert_blocked():
    case_id = "TEST5678"
    record_stage(case_id, "CASE_CLEAR", payload={"status": "CASE_CLEAR", "case_id": case_id})
    raw = json.dumps({"status": "HUMAN_ALERT", "case_id": case_id, "reason": "oops"})
    decision = evaluate_outbound("coordinator", raw, room_id="room1")
    assert decision.skip is True
    assert decision.reason == "false_human_alert"


def test_intake_ignores_non_coordinator():
    skip, reason = should_skip_inbound(
        "intake",
        _msg("please process", sender="Verification"),
        case_id="ABC123",
    )
    assert skip is True
    assert reason == "wrong_recipient"


def test_json_replaced_with_formatted_message():
    payload = {
        "status": "INTAKE_COMPLETE",
        "case_id": "NEWCASE1",
        "requester_name": "Ada Okonkwo",
        "requested_service": "Amoxicillin 500mg",
        "presenting_issue": "Throat infection",
        "urgency": "medium",
    }
    decision = evaluate_outbound("intake", json.dumps(payload), room_id="room1")
    assert decision.skip is False
    assert decision.formatted_content is not None
    assert "INTAKE COMPLETE" in decision.formatted_content
    assert is_visible_json(json.dumps(payload)) is True


@pytest.mark.parametrize(
    "stage",
    ["INTAKE_COMPLETE", "INTAKE_INCOMPLETE", "CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE", "RESOURCE_COMPLETE"],
)
def test_coordinator_cannot_send_agent_owned_stages(stage):
    raw = json.dumps({"status": stage, "case_id": f"MB-{stage}"})
    decision = evaluate_outbound("coordinator", raw, room_id="room1")
    assert decision.skip is True
    assert decision.reason == "invalid_stage_owner"


def test_intake_can_send_intake_complete():
    raw = json.dumps(
        {
            "status": "INTAKE_COMPLETE",
            "case_id": "MB-INTAKE1",
            "requester_name": "Ada Okonkwo",
            "requested_service": "Amoxicillin 500mg",
        }
    )
    decision = evaluate_outbound("intake", raw, room_id="room1")
    assert decision.skip is False
    assert decision.stage == "INTAKE_COMPLETE"


@pytest.mark.parametrize("stage", ["CASE_CLEAR", "CASE_CAUTION", "CASE_ESCALATE"])
def test_verification_can_send_verification_outcomes(stage):
    raw = json.dumps({"status": stage, "case_id": f"MB-{stage}", "requested_service": "Amoxicillin 500mg"})
    decision = evaluate_outbound("verification", raw, room_id="room1")
    assert decision.skip is False
    assert decision.stage == stage


def test_resource_can_send_resource_complete():
    raw = json.dumps({"status": "RESOURCE_COMPLETE", "case_id": "MB-RESOURCE1", "requested_service": "Amoxicillin"})
    decision = evaluate_outbound("resource", raw, room_id="room1")
    assert decision.skip is False
    assert decision.stage == "RESOURCE_COMPLETE"


def test_coordinator_can_send_case_ready():
    case_id = "MB-READY1"
    raw = json.dumps({"status": "CASE_READY", "case_id": case_id, "requested_service": "Amoxicillin"})
    decision = evaluate_outbound("coordinator", raw, room_id="room1")
    assert decision.skip is False
    assert decision.stage == "CASE_READY"
    assert decision.formatted_content is not None
    assert "CASE READY FOR HUMAN REVIEW" in decision.formatted_content


def test_record_outbound_success_does_not_record_unowned_stage():
    case_id = "MB-OWNER1"
    decision = OutboundDecision(
        stage="INTAKE_COMPLETE",
        case_id=case_id,
        agent_role="coordinator",
    )
    record_outbound_success(decision, {"status": "INTAKE_COMPLETE", "case_id": case_id}, "room1")
    assert stage_completed(case_id, "INTAKE_COMPLETE") is False


def test_coordinator_prompt_no_case_ready_json_only():
    prompt = (Path(__file__).parents[1] / "prompts" / "pharmacy" / "coordinator.md").read_text(
        encoding="utf-8"
    )
    assert "CASE_READY JSON only" not in prompt
    assert "@medband-approval-desk CASE READY FOR HUMAN REVIEW" in prompt
    assert "Human Reviewer:\n@medlabbytbr" in prompt
    assert "@Coordinator APPROVE {case_id}" in prompt
    assert "@Coordinator REJECT {case_id}: <reason>" in prompt


def test_extract_recipient_from_mentions():
    recipient = extract_recipient(
        {"content": "verify this", "mentions": ["@medlabbytbr/verification"]}
    )
    assert recipient == "verification"


def test_coordinator_processes_intake_complete_after_intake_recorded():
    case_id = "MB-TEST001"
    record_stage(
        case_id,
        "INTAKE_COMPLETE",
        payload={
            "status": "INTAKE_COMPLETE",
            "case_id": case_id,
            "requester_name": "Ada Okonkwo",
            "requested_service": "Amoxicillin 500mg",
        },
    )
    msg = _msg("📋 INTAKE COMPLETE\n\nPatient: Ada Okonkwo", sender="Intake")
    skip, reason = should_skip_inbound("coordinator", msg, case_id=case_id)
    assert skip is False


def test_coordinator_skips_intake_complete_after_verify_request():
    case_id = "MB-TEST002"
    record_stage(case_id, "INTAKE_COMPLETE", payload={"case_id": case_id})
    record_stage(case_id, "VERIFY_REQUEST", payload={"case_id": case_id})
    msg = _msg("📋 INTAKE COMPLETE\n\nPatient: Ada", sender="Intake")
    skip, reason = should_skip_inbound("coordinator", msg, case_id=case_id)
    assert skip is True
    assert reason == "duplicate_stage"


def test_intake_complete_includes_case_id():
    text = format_case_opened(
        {"case_id": "MB-ABC12345", "requester_name": "Ada", "requested_service": "Amox"}
    )
    assert "Case ID: MB-ABC12345" in text


def test_legacy_verification_summary_blocked():
    legacy = "---\n✅ Verification passed\n\nAmoxicillin is cleared.\nNo safety concerns found. Passing to Resource check now.\n---"
    decision = evaluate_outbound("verification", legacy, room_id="room1", case_id_hint="MB-TEST001")
    assert decision.skip is True
    assert decision.reason == "legacy_template"


def test_legacy_resource_summary_blocked():
    legacy = "---\n✅ Resource confirmed\n\nAmoxicillin is available at General Hospital.\nPassing full summary to Coordinator now.\n---"
    decision = evaluate_outbound("resource", legacy, room_id="room1", case_id_hint="MB-TEST002")
    assert decision.skip is True
    assert decision.reason == "legacy_template"


def test_legacy_case_ready_blocked():
    legacy = "📋 CASE READY FOR YOUR REVIEW\n\nPatient: Ada"
    decision = evaluate_outbound("coordinator", legacy, room_id="room1", case_id_hint="MB-TEST003")
    assert decision.skip is True
    assert decision.reason == "legacy_template"


def test_followup_verification_blocked_after_stage():
    case_id = "MB-TEST004"
    record_stage(case_id, "CASE_CLEAR", payload={"status": "CASE_CLEAR", "case_id": case_id})
    followup = "✅ Verification passed\n\nAmoxicillin is cleared to proceed."
    decision = evaluate_outbound("verification", followup, room_id="room1", case_id_hint=case_id)
    assert decision.skip is True
    assert decision.reason in ("legacy_template", "duplicate_summary")


def test_resource_uses_intake_context_from_postgres():
    case_id = "MB-TEST005"
    record_stage(
        case_id,
        "INTAKE_COMPLETE",
        payload={
            "status": "INTAKE_COMPLETE",
            "case_id": case_id,
            "requester_name": "Ada Okonkwo",
            "requested_service": "Amoxicillin 500mg",
            "institution_name": "Demo Institution",
            "urgency": "medium",
        },
    )
    resource_json = json.dumps(
        {
            "status": "RESOURCE_COMPLETE",
            "case_id": case_id,
            "drug_name": "Amoxicillin",
            "institution": "General Hospital",
            "in_stock": True,
            "quantity_available": 120,
        }
    )
    decision = evaluate_outbound("resource", resource_json, room_id="room1")
    assert decision.skip is False
    assert decision.formatted_content is not None
    assert "Demo Institution" in decision.formatted_content
    assert "Amoxicillin 500mg" in decision.formatted_content
    assert "General Hospital" not in decision.formatted_content


def test_case_approved_format():
    case_id = "MB-86A62017"
    record_stage(
        case_id,
        "INTAKE_COMPLETE",
        payload={
            "case_id": case_id,
            "requester_name": "Ada Okonkwo",
            "requested_service": "Amoxicillin 500mg",
        },
    )
    record_stage(case_id, "CASE_READY", payload={"status": "CASE_READY", "case_id": case_id})
    payload = json.dumps({"status": "CASE_APPROVED", "case_id": case_id, "approved_by": "Kehinde-David Damilare"})
    decision = evaluate_outbound("coordinator", payload, room_id="room1")
    assert decision.skip is False
    assert decision.formatted_content is not None
    assert "✅ CASE APPROVED" in decision.formatted_content
    assert "MB-86A62017" in decision.formatted_content
    assert "Ada Okonkwo" in decision.formatted_content
    assert "Amoxicillin 500mg" in decision.formatted_content
    assert "Approved by Kehinde-David Damilare" in decision.formatted_content
    assert "No AI approved this case" in decision.formatted_content


def test_is_legacy_band_message():
    assert is_legacy_band_message("---\n✅ Verification passed") is True
    assert is_legacy_band_message("Resource confirmed at hospital") is True
    assert is_legacy_band_message("📋 INTAKE COMPLETE\n\nPatient: Ada") is False


_VERIFY_CASE_BODY = (
    "VERIFY CASE\n\n"
    "Case ID: MEDBAND-WEB-5B75411A\n"
    "Patient: Band Human Approval Participant Test\n"
    "Request: PARACETAMOL\n"
    "Issue: BODY PAINS\n"
    "Prescription Code: TBR-DOC-0042\n\n"
    "Next Step: Confirm there are no safety concerns and reply to the Coordinator."
)

_CHECK_AVAILABILITY_BODY = (
    "CHECK AVAILABILITY\n\n"
    "Case ID: MEDBAND-WEB-5B75411A\n"
    "Request: PARACETAMOL\n"
    "Institution: Demo Institution\n\n"
    "Next Step: Confirm stock and reply to the Coordinator."
)


def test_coordinator_verify_case_via_mentions_is_verify_request():
    # A. Clean header + mention payload, no full @handle in visible content.
    decision = evaluate_outbound(
        "coordinator",
        _VERIFY_CASE_BODY,
        room_id="room1",
        recipient="verification",
    )
    assert decision.skip is False
    assert decision.stage == "VERIFY_REQUEST"
    assert decision.case_id == "MEDBAND-WEB-5B75411A"
    assert "@MEDLABBYTBR/VERIFICATION" not in _VERIFY_CASE_BODY.upper()


def test_coordinator_check_availability_via_mentions_is_resource_request():
    # B. Clean header + mention payload, no full @handle in visible content.
    decision = evaluate_outbound(
        "coordinator",
        _CHECK_AVAILABILITY_BODY,
        room_id="room1",
        recipient="resource",
    )
    assert decision.skip is False
    assert decision.stage == "RESOURCE_REQUEST"
    assert decision.case_id == "MEDBAND-WEB-5B75411A"
    assert "@MEDLABBYTBR/RESOURCE" not in _CHECK_AVAILABILITY_BODY.upper()


def test_verify_case_without_verification_mention_not_verify_request():
    # C. No Verification mention -> must not be promoted to VERIFY_REQUEST.
    decision = evaluate_outbound(
        "coordinator",
        _VERIFY_CASE_BODY,
        room_id="room1",
        recipient="room",
    )
    assert decision.stage != "VERIFY_REQUEST"
    assert decision.skip is True
    assert decision.reason == "unformatted_message"


def test_non_coordinator_cannot_infer_verify_request_from_mentions():
    # D. Only the Coordinator may originate VERIFY_REQUEST, even with the mention.
    for role in ("intake", "verification", "resource"):
        decision = evaluate_outbound(
            role,
            _VERIFY_CASE_BODY,
            room_id="room1",
            recipient="verification",
        )
        assert decision.stage != "VERIFY_REQUEST"
        assert decision.skip is True
