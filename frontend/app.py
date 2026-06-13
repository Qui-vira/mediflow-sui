"""Flask web form backend for MedBand case intake."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.reports import build_patient_report
from core.sector_loader import SECTOR_META, sector_meta, set_sector
from core.workflow import load_case, run_case, run_case_stream

app = Flask(__name__, template_folder=".")


def _form_raw(data) -> tuple[str, str]:
    sector = data.get("sector", os.getenv("ACTIVE_SECTOR", "pharmacy"))
    set_sector(sector)
    os.environ["ACTIVE_SECTOR"] = sector

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
    case = load_case(case_id.upper())
    if not case:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(case)


@app.route("/submit", methods=["POST"])
def submit():
    raw, sector = _form_raw(request.form)
    try:
        result = run_case(raw, sector=sector)
        result["patient_report"] = build_patient_report(result)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "ERROR"}), 500


@app.route("/submit/stream", methods=["POST"])
def submit_stream():
    raw, sector = _form_raw(request.form)

    def generate():
        try:
            for event in run_case_stream(raw, sector=sector):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "error": str(exc)}) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@app.route("/api/lookup/<case_id>")
def lookup(case_id):
    case = load_case(case_id.upper())
    if not case:
        return jsonify({"error": "Case not found"}), 404
    report = build_patient_report(case)
    return jsonify({"case": case, "report": report, "sector": sector_meta(case.get("sector"))})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "MedBand"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
