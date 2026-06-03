"""Load sector-specific prompts and data based on ACTIVE_SECTOR."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ACTIVE_SECTOR = os.getenv("ACTIVE_SECTOR", "pharmacy")

SECTORS = [
    "pharmacy",
    "hospital_triage",
    "lab",
    "mental_health",
    "hmo_claims",
    "emergency",
]

HUMAN_ROLES = {
    "pharmacy": "Pharmacist",
    "hospital_triage": "Doctor / Nurse",
    "lab": "Lab Officer",
    "mental_health": "Clinical Coordinator",
    "hmo_claims": "Claims Officer",
    "emergency": "Dispatcher",
}

VERIFICATION_DATA_FILES = {
    "pharmacy": ["registry.json", "risk_table.json"],
    "hospital_triage": ["triage_criteria.json"],
    "lab": ["test_catalog.json", "referral_rules.json"],
    "mental_health": ["risk_screening.json"],
    "hmo_claims": ["policy_rules.json", "coverage_limits.json"],
    "emergency": ["severity_rules.json"],
}

RESOURCE_DATA_FILES = {
    "pharmacy": ["resources.json"],
    "hospital_triage": ["beds.json"],
    "lab": ["lab_slots.json"],
    "mental_health": ["therapist_availability.json"],
    "hmo_claims": ["coverage_table.json"],
    "emergency": ["units.json"],
}


def set_sector(sector: str):
    global ACTIVE_SECTOR
    if sector not in SECTORS:
        raise ValueError(f"Unknown sector: {sector}. Must be one of {SECTORS}")
    ACTIVE_SECTOR = sector
    os.environ["ACTIVE_SECTOR"] = sector


def load_prompt(agent_name: str) -> str:
    path = ROOT / "prompts" / ACTIVE_SECTOR / f"{agent_name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_data(filename: str) -> dict | list:
    path = ROOT / "data" / ACTIVE_SECTOR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_verification_data() -> dict:
    return {
        f.replace(".json", ""): load_data(f)
        for f in VERIFICATION_DATA_FILES.get(ACTIVE_SECTOR, [])
    }


def load_resource_data() -> dict:
    return {
        f.replace(".json", ""): load_data(f)
        for f in RESOURCE_DATA_FILES.get(ACTIVE_SECTOR, [])
    }


def human_role() -> str:
    return HUMAN_ROLES.get(ACTIVE_SECTOR, "Human Professional")
