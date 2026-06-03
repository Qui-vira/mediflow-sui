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
from core.sector_loader import SECTOR_META, sector_meta
from core.workflow import load_case, run_case, run_case_stream

app = Flask(__name__, template_folder=".")


def _form_raw(data) -> tuple[str, str]:
    sector = data.get("sector", os.getenv("ACTIVE_SECTOR", "pharmacy"))
    os.environ["ACTIVE_SECTOR"] = sector
    raw = f"""
Name: {data.get('name', '')}
Issue: {data.get('issue', '')}
Requested service: {data.get('service', '')}
Urgency: {data.get('urgency', '')}
Sector: {sector}
""".strip()
    return raw, sector


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
