"""Streamlit human approval dashboard for MedBand."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.audit_log import get_log, post
from core.sector_loader import ACTIVE_SECTOR, human_role
from core.workflow import list_cases, load_case

st.set_page_config(page_title="MedBand Dashboard", page_icon="🏥", layout="wide")

st.title("MedBand — Human Approval Dashboard")
st.caption(
    f"**The Billionaire Republic (TBR)** | Sector: **{ACTIVE_SECTOR}** | "
    f"Approver: **{human_role()}**"
)

st.info(
    "AI agents prepare, verify, flag, and summarize cases. "
    "They do **not** prescribe, approve, or make clinical decisions. "
    "Final approval belongs to the human professional."
)

case_ids = list_cases()
selected = st.sidebar.selectbox("Select Case", case_ids if case_ids else ["— none —"])

if not case_ids:
    st.warning("No cases yet. Submit a case via the web form first.")
    st.markdown("```bash\npython frontend/app.py\n```")
    st.markdown("Open http://localhost:5000")
    st.stop()

case = load_case(selected)
if not case:
    st.error(f"Could not load case {selected}")
    st.stop()

case_id = case.get("case_id", "UNKNOWN")
status = case.get("status", "UNKNOWN")

st.subheader("Case Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Case ID", case_id)
col2.metric("Status", status)
col3.metric("Sector", case.get("sector", ACTIVE_SECTOR))
col4.metric("Human Role", case.get("human_role", human_role()))

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Intake", "Verification", "Resource", "Audit Trail"])

with tab1:
    st.subheader("Intake Result")
    intake = case.get("intake", {})
    if intake:
        st.json(intake)
    else:
        st.write("No intake data.")

with tab2:
    st.subheader("Verification Result")
    verification = case.get("verification", {})
    if verification:
        vstatus = verification.get("status", "N/A")
        if vstatus == "CASE_ESCALATE":
            st.error(f"Escalation: {verification.get('reason', 'Review required immediately')}")
        elif vstatus == "CASE_CAUTION":
            st.warning(f"Caution: {verification.get('reason', 'Review recommended')}")
        else:
            st.success(f"Status: {vstatus}")
        st.json(verification)
    else:
        st.write("Verification skipped (escalated before resource check).")

with tab3:
    st.subheader("Resource Result")
    resource = case.get("resource", {})
    if resource:
        st.json(resource)
    else:
        st.write("Resource check skipped (case escalated).")

with tab4:
    st.subheader("Audit Trail (Mock Band Room)")
    audit_trail = case.get("audit_trail") or get_log(case_id)
    st.caption(f"{len(audit_trail)} entries from audit_log")
    if audit_trail:
        for entry in audit_trail:
            ts = entry.get("timestamp", "")
            agent = entry.get("agent", "")
            estatus = entry.get("status", "")
            with st.expander(f"[{ts}] {agent} → {estatus}", expanded=False):
                st.json(entry.get("data", {}))
    else:
        st.write("No audit entries.")

st.divider()
st.subheader("Human Decision")

decision_key = f"decision_{case_id}"
if decision_key not in st.session_state:
    st.session_state[decision_key] = None

notes_key = f"notes_{case_id}"
notes = st.text_area("Decision notes (optional)", key=notes_key)

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("Approve", type="primary", use_container_width=True):
        decision = {
            "decision": "APPROVED",
            "by": human_role(),
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "case_id": case_id,
            "notes": notes,
        }
        st.session_state[decision_key] = decision
        post("human", "APPROVED", case_id, decision)
        st.success(f"Case {case_id} APPROVED by {human_role()}")

with col_b:
    if st.button("Reject", use_container_width=True):
        decision = {
            "decision": "REJECTED",
            "by": human_role(),
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "case_id": case_id,
            "notes": notes,
        }
        st.session_state[decision_key] = decision
        post("human", "REJECTED", case_id, decision)
        st.error(f"Case {case_id} REJECTED by {human_role()}")

with col_c:
    if st.button("Request More Info", use_container_width=True):
        decision = {
            "decision": "MORE_INFO_REQUESTED",
            "by": human_role(),
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "case_id": case_id,
            "notes": notes or "Additional information required from requester.",
        }
        st.session_state[decision_key] = decision
        post("human", "MORE_INFO_REQUESTED", case_id, decision)
        st.warning(f"Case {case_id} — more info requested by {human_role()}")

if st.session_state[decision_key]:
    st.json(st.session_state[decision_key])
