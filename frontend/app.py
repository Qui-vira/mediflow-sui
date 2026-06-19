"""Flask web form backend for MedBand case intake."""
import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request
from flask_compress import Compress

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.band_client import save_pending_case, send_to_coordinator_sync
from core.reports import build_patient_report
from core.sector_loader import (
    SECTOR_META,
    band_room_name,
    get_active_sector,
    get_institution,
    human_role,
    load_institutions,
    preload_all_caches,
    sector_meta,
    set_active_sector,
)
from core.workflow import load_case, run_case, run_case_stream

app = Flask(__name__, template_folder=".")
Compress(app)

BAND_MODE = os.environ.get("BAND_MODE", "true").lower() == "true"

preload_all_caches()


@app.after_request
def add_cache_headers(response):
    if request.path.startswith("/static/"):
        response.cache_control.max_age = 86400
        response.cache_control.public = True
    return response


def _form_raw(data) -> tuple[str, str]:
    sector = data.get("sector", "pharmacy")
    set_active_sector(sector)

    lines = [f"Sector: {sector}"]

    name = data.get("name", "")
    issue = data.get("issue", "")
    service = data.get("service", "")

    if sector == "emergency":
        service = data.get("emergency_type", service)
        lines.extend([
            f"Caller name: {name}",
            f"Emergency type: {service}",
            f"Location: {data.get('location', '')}",
            f"Additional details: {issue}",
        ])
    elif sector == "mental_health":
        self_harm = data.get("self_harm_flag") in ("true", "on", "1", True)
        lines.extend([
            f"Name: {name}",
            f"Presenting concern: {issue}",
            f"Duration: {data.get('duration', '')}",
            f"Self harm flag: {self_harm}",
            f"Requested service: {service or issue}",
            f"Urgency: {data.get('urgency', 'medium')}",
        ])
    elif sector == "hospital_triage":
        lines.extend([
            f"Name: {name}",
            f"Chief complaint: {issue}",
            f"Vitals description: {data.get('vitals_description', '')}",
            f"Requested service: {service or issue}",
            f"Urgency: {data.get('urgency', 'high')}",
        ])
    elif sector == "lab":
        lines.extend([
            f"Name: {name}",
            f"Test requested: {service}",
            f"Referral number: {data.get('referral_number', '')}",
            f"Patient ID: {data.get('patient_id', '')}",
            f"Clinical notes: {issue}",
            f"Urgency: {data.get('urgency', 'medium')}",
        ])
    elif sector == "hmo_claims":
        lines.extend([
            f"Requester name: {name}",
            f"Procedure code: {service}",
            f"Policy number: {data.get('policy_number', '')}",
            f"Provider name: {data.get('provider_name', '')}",
            f"Claim notes: {issue}",
            f"Urgency: {data.get('urgency', 'low')}",
        ])
    else:
        lines.extend([
            f"Name: {name}",
            f"Issue: {issue}",
            f"Requested service: {service}",
            f"Urgency: {data.get('urgency', 'high')}",
        ])
        if data.get("prescription_code"):
            lines.append(f"Prescription code: {data.get('prescription_code')}")

    return "\n".join(lines), sector


def _form_patient_name(data) -> str:
    return (data.get("name") or data.get("caller_name") or "Patient").strip()


def _form_urgency(data, sector: str) -> str:
    defaults = {
        "hospital_triage": "high",
        "emergency": "critical",
        "hmo_claims": "low",
    }
    return data.get("urgency") or defaults.get(sector, "medium")


def _form_requested_service(data, sector: str) -> str:
    if sector == "emergency":
        return data.get("emergency_type") or data.get("service", "")
    return data.get("service", "")


def _build_band_case_payload(data, raw_input: str, sector: str) -> dict:
    institution_id = data.get("institution_id") or None
    institution = get_institution(sector, institution_id) if institution_id else None
    case_id = f"MEDIFLOW-WEB-{str(uuid.uuid4())[:8].upper()}"

    return {
        "case_id": case_id,
        "sector": sector,
        "institution_id": institution_id,
        "institution_name": (institution or {}).get("name"),
        "patient_name": _form_patient_name(data),
        # Structured fields preserved from the web form so the Coordinator can
        # forward them to Intake verbatim (presenting_issue must not become
        # "Not specified", requested_service must stay intact).
        "presenting_issue": data.get("issue", ""),
        "requested_service": _form_requested_service(data, sector),
        "prescription_code": data.get("prescription_code", ""),
        "raw_input": raw_input,
        "urgency": _form_urgency(data, sector),
        "source": "web_form",
        "turnaround": (institution or {}).get("turnaround"),
    }


def _submit_via_band(data, raw_input: str, sector: str) -> dict:
    case_payload = _build_band_case_payload(data, raw_input, sector)
    save_pending_case(case_payload)
    institution_id = case_payload.get("institution_id")
    band_room = band_room_name(case_payload["case_id"], sector, institution_id)

    result = {
        "case_id": case_payload["case_id"],
        "status": "processing",
        "message": "Your case has been sent to the agents.",
        "band_room": band_room,
        "track_url": f"/status?case_id={case_payload['case_id']}",
        "human_role": human_role(sector),
        "turnaround": case_payload.get("turnaround"),
        "institution_name": case_payload.get("institution_name"),
    }

    def _send_async():
        try:
            send_to_coordinator_sync(case_payload)
        except Exception:
            pass

    threading.Thread(target=_send_async, daemon=True).start()
    return result


def _band_stream_events(data, raw_input: str, sector: str):
    """NDJSON events for Band mode (immediate ack; agents run in background)."""
    try:
        result = _submit_via_band(data, raw_input, sector)
        yield {
            "type": "band_submitted",
            **result,
        }
        for agent in ("coordinator", "intake", "verification", "resource"):
            yield {
                "type": "agent_active",
                "agent": agent,
                "message": "Processing on Band…",
                "case_id": result["case_id"],
            }
            yield {
                "type": "agent_done",
                "agent": agent,
                "status": "PROCESSING",
                "case_id": result["case_id"],
            }
    except Exception as exc:
        yield {"type": "error", "error": str(exc)}


# Web-submitted cases save a local JSON snapshot with a fixed status of
# "PROCESSING" (see core.band_client.save_pending_case). The live workflow
# stages - including CASE_APPROVED / CASE_REJECTED - are recorded only in
# Postgres by the Band agents, so the snapshot status goes stale and the status
# page is stuck on PROCESSING. Derive the display status from the recorded
# stages instead, highest-priority (most advanced / terminal) stage first.
_STAGE_DISPLAY_STATUS = (
    ("CASE_APPROVED", "APPROVED"),
    ("CASE_REJECTED", "REJECTED"),
    ("HUMAN_ALERT", "ESCALATED"),
    ("CASE_ESCALATE", "ESCALATED"),
    ("CASE_READY", "AWAITING HUMAN REVIEW"),
    ("RESOURCE_COMPLETE", "READY FOR HUMAN REVIEW"),
    ("RESOURCE_REQUEST", "CHECKING AVAILABILITY"),
    ("CASE_CLEAR", "VERIFIED"),
    ("CASE_CAUTION", "VERIFIED"),
    ("VERIFY_REQUEST", "VERIFYING"),
    ("INTAKE_COMPLETE", "INTAKE COMPLETE"),
    ("CASE_OPENED", "OPENED"),
)


def _apply_live_status(case: dict) -> dict:
    """Override the stale local snapshot status with one derived from the
    workflow stages recorded in Postgres.

    Falls back to the snapshot status untouched if no stages are recorded yet or
    the lookup fails, so the status endpoints never break on a DB hiccup.
    """
    case_id = case.get("case_id")
    if not case_id:
        return case
    try:
        from core.case_state import completed_stages

        stages = completed_stages(case_id)
    except Exception:
        return case
    for stage, display in _STAGE_DISPLAY_STATUS:
        if stage in stages:
            case["status"] = display
            break
    return case


def _case_from_stages(case_id: str) -> dict | None:
    """Reconstruct a minimal case view from Postgres workflow stages when the
    local JSON snapshot is missing.

    The snapshot lives on the web container's ephemeral filesystem, so it is
    lost on redeploy. Recorded stages survive in Postgres, so an already-decided
    case still resolves (e.g. shows APPROVED) without the patient resubmitting.
    """
    try:
        from core.case_state import get_case_state

        state = get_case_state(case_id)
    except Exception:
        return None
    if not state.get("completed_stages"):
        return None
    intake = state.get("intake") or {}
    opened = state.get("opened") or {}
    return {
        "case_id": case_id,
        "sector": intake.get("sector") or opened.get("sector"),
        "institution_name": intake.get("institution_name") or opened.get("institution_name"),
        "intake": {
            "requester_name": intake.get("requester_name") or opened.get("requester_name"),
            "requested_service": intake.get("requested_service") or opened.get("requested_service"),
        },
        "verification": state.get("verification") or {},
        "resource": state.get("resource") or {},
    }


def _load_case_for_status(case_id: str) -> dict | None:
    """Load a case for the status endpoints: prefer the local snapshot, fall
    back to Postgres stages, then always derive the live status from stages."""
    case_id = case_id.upper()
    case = load_case(case_id) or _case_from_stages(case_id)
    if not case:
        return None
    return _apply_live_status(case)


@app.route("/")
def index():
    return render_template("index.html", sectors=SECTOR_META)


@app.route("/status")
def status_page():
    return render_template("status.html")


@app.route("/api/sectors")
def api_sectors():
    return jsonify(SECTOR_META)


@app.route("/api/case/<case_id>")
def api_case(case_id):
    case = _load_case_for_status(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(case)


@app.route("/submit", methods=["POST"])
def submit():
    # Copy request data into a plain dict while the request context is active,
    # so nothing downstream (threads/background work) touches the Flask request.
    form_data = request.form.to_dict()
    raw, sector = _form_raw(form_data)
    institution_id = form_data.get("institution_id") or None
    try:
        if BAND_MODE:
            return jsonify(_submit_via_band(form_data, raw, sector))
        result = run_case(raw, sector=sector, institution_id=institution_id)
        result["patient_report"] = build_patient_report(result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "ERROR"}), 500


@app.route("/submit/stream", methods=["POST"])
def submit_stream():
    # Copy request data into a plain dict before the streaming generator runs.
    # Flask iterates `generate()` after the request context is torn down, so any
    # `request.*` access inside it would raise "Working outside of request context".
    form_data = request.form.to_dict()
    raw, sector = _form_raw(form_data)
    institution_id = form_data.get("institution_id") or None

    def generate():
        try:
            if BAND_MODE:
                for event in _band_stream_events(form_data, raw, sector):
                    yield json.dumps(event) + "\n"
                return
            for event in run_case_stream(raw, sector=sector, institution_id=institution_id):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "error": str(exc)}) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@app.route("/api/lookup/<case_id>")
def lookup(case_id):
    case = _load_case_for_status(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    report = build_patient_report(case)
    return jsonify({"case": case, "report": report, "sector": sector_meta(case.get("sector"))})


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/api/institutions/<sector>")
def get_institutions(sector):
    return jsonify(load_institutions(sector))


@app.route("/api/register", methods=["POST"])
def register_institution():
    data = request.get_json(silent=True) or {}
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["status"] = "pending"
    data["id"] = str(uuid.uuid4())[:8].upper()

    reg_path = ROOT / "data" / "registrations.json"
    registrations = []
    if reg_path.exists():
        with open(reg_path, encoding="utf-8") as f:
            registrations = json.load(f)
    registrations.append(data)
    reg_path.parent.mkdir(exist_ok=True)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registrations, f, indent=2)

    return jsonify({
        "success": True,
        "message": "Registration received",
        "id": data["id"],
    })


@app.route("/api/admin/registrations")
def view_registrations():
    reg_path = ROOT / "data" / "registrations.json"
    if reg_path.exists():
        with open(reg_path, encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route("/landing")
def landing_redirect():
    return redirect("https://medband-landing.vercel.app")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "MedBand",
        "band_mode": BAND_MODE,
        "landing": "https://medband-landing.vercel.app",
        "form": "https://web-production-6d13b.up.railway.app",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
