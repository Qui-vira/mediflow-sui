"""Streamlit human approval dashboard for MedBand."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.audit_log import get_log
from core.reports import build_patient_report
from core.sector_loader import ACTIVE_SECTOR, HUMAN_ROLES, SECTOR_META, human_role, sector_meta
from core.workflow import list_cases, load_case, save_decision

st.set_page_config(page_title="MedBand Dashboard", page_icon="🏥", layout="wide")

AGENT_ICONS = {
    "coordinator": "🎯",
    "intake": "📋",
    "verification": "🔍",
    "resource": "📦",
    "human": "👤",
}

SKIP_KEYS = {"case_id", "status", "parse_error", "raw"}

INTAKE_LABELS = {
    "pharmacy": {
        "requester_name": "Patient Name",
        "requested_service": "Requested Drug",
        "presenting_issue": "Presenting Issue",
        "prescription_code": "Prescription Code",
        "urgency": "Urgency",
    },
    "hospital_triage": {
        "requester_name": "Patient Name",
        "chief_complaint": "Chief Complaint",
        "vitals_description": "Vitals",
        "requested_service": "Service",
        "urgency": "Urgency",
    },
    "lab": {
        "requester_name": "Patient Name",
        "test_requested": "Test Requested",
        "referral_number": "Referral Number",
        "patient_id": "Patient ID",
        "requested_service": "Test",
    },
    "mental_health": {
        "requester_name": "Patient Name",
        "presenting_concern": "Presenting Concern",
        "duration": "Duration",
        "self_harm_flag": "Self-Harm Flag",
        "requested_service": "Service",
    },
    "hmo_claims": {
        "requester_name": "Requester Name",
        "procedure_code": "Procedure Code",
        "policy_number": "Policy Number",
        "provider_name": "Provider",
        "requested_service": "Procedure",
    },
    "emergency": {
        "caller_name": "Caller Name",
        "requester_name": "Caller",
        "emergency_type": "Emergency Type",
        "location": "Location",
        "additional_details": "Details",
        "requested_service": "Emergency Type",
    },
}


def labelize(key: str, sector: str = None) -> str:
    sector = sector or ACTIVE_SECTOR
    if sector in INTAKE_LABELS and key in INTAKE_LABELS[sector]:
        return INTAKE_LABELS[sector][key]
    return key.replace("_", " ").strip().title()


def render_fields(data: dict, skip: set | None = None, sector: str = None):
    skip = skip or SKIP_KEYS
    if not data:
        st.write("No data available.")
        return
    for key, value in data.items():
        if key in skip or value in (None, "", []):
            continue
        if isinstance(value, list):
            if not value:
                continue
            if isinstance(value[0], dict):
                st.markdown(f"**{labelize(key, sector)}**")
                for item in value:
                    parts = [f"{labelize(k, sector)}: {v}" for k, v in item.items() if v not in (None, "")]
                    st.markdown(f"- {' | '.join(parts)}")
            else:
                st.markdown(f"**{labelize(key, sector)}:** {', '.join(str(v) for v in value)}")
        elif isinstance(value, dict):
            st.markdown(f"**{labelize(key, sector)}**")
            render_fields(value, skip=set(), sector=sector)
        else:
            st.markdown(f"**{labelize(key, sector)}:** {value}")


def status_color(status: str) -> str:
    if status in ("READY_FOR_REVIEW", "CASE_CLEAR", "APPROVED", "INTAKE_COMPLETE", "RESOURCE_COMPLETE"):
        return "#00c896"
    if status in ("CASE_CAUTION", "INCOMPLETE", "MORE_INFO_REQUESTED"):
        return "#fbbf24"
    if status in ("ESCALATED", "CASE_ESCALATE", "HUMAN_ALERT", "REJECTED"):
        return "#ef4444"
    return "#8b9cb3"


def render_timeline(audit_trail: list, sector: str):
    st.markdown(
        """
        <style>
        .tl-wrap { position: relative; padding-left: 1.5rem; margin: 1rem 0; }
        .tl-wrap::before {
            content: ""; position: absolute; left: 0.45rem; top: 0; bottom: 0;
            width: 2px; background: #2d3a4f;
        }
        .tl-entry {
            position: relative; margin-bottom: 1.25rem; padding: 0.85rem 1rem;
            background: #141b26; border-radius: 10px; border: 1px solid #2d3a4f;
        }
        .tl-entry::before {
            content: ""; position: absolute; left: -1.35rem; top: 1.1rem;
            width: 10px; height: 10px; border-radius: 50%; background: var(--dot-color, #00c896);
        }
        .tl-head { display: flex; justify-content: space-between; align-items: center; }
        .tl-agent { font-weight: 700; font-size: 0.95rem; }
        .tl-time { font-size: 0.75rem; color: #8b9cb3; }
        .tl-status {
            display: inline-block; margin-top: 0.35rem; padding: 0.15rem 0.5rem;
            border-radius: 4px; font-size: 0.75rem; font-weight: 600;
            background: rgba(0,200,150,0.12); color: var(--dot-color, #00c896);
        }
        .tl-body { margin-top: 0.5rem; font-size: 0.85rem; color: #c5d0de; line-height: 1.5; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for entry in audit_trail:
        agent = entry.get("agent", "unknown")
        estatus = entry.get("status", "")
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        data = entry.get("data", {})
        color = status_color(estatus)
        icon = AGENT_ICONS.get(agent, "⚪")

        summary_parts = []
        for key in ("requester_name", "requested_service", "drug_name", "reason", "action", "human_role", "decision"):
            if data.get(key):
                summary_parts.append(f"{labelize(key, sector)}: {data[key]}")
        if data.get("notes"):
            summary_parts.append(f"Notes: {data['notes']}")
        body = " · ".join(summary_parts) if summary_parts else "Step recorded in audit log."

        st.markdown(
            f'<div class="tl-wrap"><div class="tl-entry" style="--dot-color:{color}">'
            f'<div class="tl-head"><span class="tl-agent">{icon} {agent.title()} Agent</span>'
            f'<span class="tl-time">{ts}</span></div>'
            f'<span class="tl-status" style="--dot-color:{color}">{estatus.replace("_", " ")}</span>'
            f'<div class="tl-body">{body}</div></div></div>',
            unsafe_allow_html=True,
        )


def _self_harm_flagged(intake: dict) -> bool:
    flag = intake.get("self_harm_flag")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.lower() in ("true", "yes", "1"):
        return True
    return False


def _role_for_case(case: dict) -> str:
    sector = case.get("sector", ACTIVE_SECTOR)
    return case.get("human_role") or HUMAN_ROLES.get(sector, human_role())


meta = sector_meta(ACTIVE_SECTOR)
st.markdown(
    f'<div style="padding:0.75rem 1rem;background:{meta["color"]}18;border-left:4px solid {meta["color"]};'
    f'border-radius:8px;margin-bottom:1rem">'
    f'<strong>{meta["icon"]} {meta["label"]}</strong> · Default approver: <strong>{human_role()}</strong></div>',
    unsafe_allow_html=True,
)

st.title("MedBand - Human Approval Dashboard")
st.caption("The Billionaire Republic (TBR) · Band of Agents Hackathon 2026")

st.info(
    "AI agents prepare, verify, flag, and summarize. They do **not** prescribe or approve. "
    "Your decision is sent back to the requester on the Case Status page."
)

case_ids = list_cases()
selected = st.sidebar.selectbox("Select Case", case_ids if case_ids else ["No cases yet"])

if not case_ids:
    st.warning("No cases yet. Submit a case via the web form first.")
    st.markdown("Run `python frontend/app.py` then open http://localhost:5000")
    st.stop()

case = load_case(selected)
if not case:
    st.error(f"Could not load case {selected}")
    st.stop()

case_id = case.get("case_id", "UNKNOWN")
status = case.get("status", "UNKNOWN")
case_sector = case.get("sector", ACTIVE_SECTOR)
case_meta = sector_meta(case_sector)
case_role = _role_for_case(case)
intake = case.get("intake", {})
verification = case.get("verification", {})
resource = case.get("resource", {})

if case_sector == "mental_health" and _self_harm_flagged(intake):
    st.markdown(
        '<div style="padding:1rem;background:#ef444422;border:2px solid #ef4444;border-radius:8px;'
        'margin-bottom:1rem;font-weight:700;color:#ef4444;">'
        "SELF-HARM RISK FLAGGED - Immediate human review required</div>",
        unsafe_allow_html=True,
    )

if case_sector == "emergency" and resource:
    unit_type = resource.get("unit_type", "")
    eta = resource.get("eta_minutes", "")
    contact = resource.get("contact_number", "")
    nearest = resource.get("nearest_unit", "")
    if unit_type or nearest:
        st.markdown(
            f'<div style="padding:1rem;background:#ef444418;border-left:4px solid #ef4444;'
            f'border-radius:8px;margin-bottom:1rem">'
            f"<strong>🚨 Dispatch Unit Assigned</strong><br>"
            f"Unit: <strong>{nearest or 'Pending'}</strong> ({unit_type}) · "
            f"ETA: <strong>{eta} min</strong> · Contact: <strong>{contact or 'N/A'}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Case ID", case_id)
col2.metric("Status", status.replace("_", " ").title())
col3.metric("Sector", case_meta["label"])
col4.metric("Human Role", case_role)

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("Agent Timeline")
    audit_trail = case.get("audit_trail") or get_log(case_id)
    st.caption(f"{len(audit_trail)} messages · mock Band room")
    render_timeline(audit_trail, case_sector)

with right:
    st.subheader("Case Details")

    with st.expander("Intake", expanded=True):
        render_fields(intake, sector=case_sector)

    with st.expander("Verification", expanded=bool(verification)):
        if verification:
            vstatus = verification.get("status", "N/A")
            if vstatus == "CASE_ESCALATE":
                st.error(verification.get("reason", "Escalation required"))
            elif vstatus == "CASE_CAUTION":
                st.warning(verification.get("reason", "Review recommended"))
            else:
                st.success(verification.get("reason", vstatus))
            render_fields(verification, skip={"reason", "recommendation"}, sector=case_sector)
        else:
            st.write("Skipped (escalated).")

    with st.expander("Resource", expanded=bool(resource)):
        if resource:
            render_fields(resource, sector=case_sector)
        else:
            st.write("Skipped (escalated).")

    report = case.get("patient_report") or build_patient_report(case)
    st.subheader("Requester Report Preview")
    st.markdown(f"**{report['headline']}**")
    for line in report.get("summary_lines", []):
        st.markdown(f"- {line}")

st.divider()
st.subheader(f"Human Decision ({case_role})")

notes = st.text_area("Decision notes (optional)", key=f"notes_{case_id}")
col_a, col_b, col_c = st.columns(3)

decision = case.get("decision")

if col_a.button("Approve", type="primary", use_container_width=True):
    decision = {
        "decision": "APPROVED",
        "by": case_role,
        "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_id": case_id,
        "notes": notes,
    }
    save_decision(case_id, decision)
    st.success(f"Case {case_id} approved. Requester can view report at /status?id={case_id}")
    st.rerun()

if col_b.button("Reject", use_container_width=True):
    decision = {
        "decision": "REJECTED",
        "by": case_role,
        "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_id": case_id,
        "notes": notes,
    }
    save_decision(case_id, decision)
    st.error(f"Case {case_id} rejected. Requester notified via status page.")
    st.rerun()

if col_c.button("Request More Info", use_container_width=True):
    decision = {
        "decision": "MORE_INFO_REQUESTED",
        "by": case_role,
        "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_id": case_id,
        "notes": notes or "Additional information required.",
    }
    save_decision(case_id, decision)
    st.warning(f"More info requested for case {case_id}.")
    st.rerun()

if decision:
    st.markdown("---")
    st.markdown(f"**Current decision:** {decision['decision'].replace('_', ' ').title()}")
    st.markdown(f"By **{decision['by']}** at {decision['at'][:19]}")
    if decision.get("notes"):
        st.markdown(f"Notes: {decision['notes']}")
    st.markdown(f"Requester link: http://localhost:5000/status?id={case_id}")
