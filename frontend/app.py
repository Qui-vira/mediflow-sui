"""Flask web form backend for MedBand case intake."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from core.audit_log import clear
from core.workflow import run_case

app = Flask(__name__, template_folder=".")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    clear()
    data = request.form
    sector = data.get("sector", os.getenv("ACTIVE_SECTOR", "pharmacy"))
    os.environ["ACTIVE_SECTOR"] = sector

    raw = f"""
Name: {data.get('name', '')}
Issue: {data.get('issue', '')}
Requested service: {data.get('service', '')}
Urgency: {data.get('urgency', '')}
Sector: {sector}
""".strip()

    try:
        result = run_case(raw, sector=sector)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "status": "ERROR"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
