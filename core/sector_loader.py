"""Load sector-specific prompts and data based on per-request sector context."""
import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_local = threading.local()

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

SECTOR_META = {
    "pharmacy": {"label": "Pharmacy", "color": "#00c896", "icon": "💊"},
    "hospital_triage": {"label": "Hospital Triage", "color": "#4da6ff", "icon": "🏥"},
    "lab": {"label": "Lab / Diagnostics", "color": "#a78bfa", "icon": "🔬"},
    "mental_health": {"label": "Mental Health", "color": "#2dd4bf", "icon": "🧠"},
    "hmo_claims": {"label": "HMO / Insurance", "color": "#fbbf24", "icon": "📋"},
    "emergency": {"label": "Emergency Dispatch", "color": "#ef4444", "icon": "🚨"},
}

SECTOR_DISPLAY_NAMES = {
    "pharmacy": "Pharmacy",
    "hospital_triage": "Hospital Triage",
    "lab": "Lab and Diagnostics",
    "mental_health": "Mental Health",
    "hmo_claims": "HMO and Insurance Claims",
    "emergency": "Emergency Dispatch",
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


def set_active_sector(sector: str) -> None:
    if sector not in SECTORS:
        raise ValueError(f"Unknown sector: {sector}. Must be one of {SECTORS}")
    _local.sector = sector


def get_active_sector() -> str:
    return getattr(_local, "sector", os.getenv("ACTIVE_SECTOR", "pharmacy"))


def set_sector(sector: str) -> None:
    """Set per-request sector; also updates env for worker subprocess compatibility."""
    set_active_sector(sector)
    os.environ["ACTIVE_SECTOR"] = sector


def sector_slug(sector: str | None = None) -> str:
    """Uppercase sector token for Band room names (e.g. pharmacy -> PHARMACY)."""
    s = sector or get_active_sector()
    return s.upper().replace("_", "")


def sector_meta(sector: str | None = None) -> dict:
    s = sector or get_active_sector()
    return SECTOR_META.get(s, {"label": s, "color": "#00c896", "icon": "🏥"})


def load_prompt(agent_name: str) -> str:
    path = ROOT / "prompts" / get_active_sector() / f"{agent_name}.md"
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_data(filename: str) -> dict | list:
    path = ROOT / "data" / get_active_sector() / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_verification_data() -> dict:
    sector = get_active_sector()
    return {
        f.replace(".json", ""): load_data(f)
        for f in VERIFICATION_DATA_FILES.get(sector, [])
    }


def load_resource_data() -> dict:
    sector = get_active_sector()
    return {
        f.replace(".json", ""): load_data(f)
        for f in RESOURCE_DATA_FILES.get(sector, [])
    }


def human_role(sector: str | None = None) -> str:
    return HUMAN_ROLES.get(sector or get_active_sector(), "Human Professional")


def _load_institutions_index() -> dict:
    path = ROOT / "data" / "institutions.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_institutions(sector: str | None = None) -> list:
    sector = sector or get_active_sector()
    return _load_institutions_index().get(sector, [])


def get_institution(sector: str, institution_id: str) -> dict | None:
    for inst in load_institutions(sector):
        if inst.get("id") == institution_id:
            return inst
    return None


def band_room_name(
    case_id: str,
    sector: str | None = None,
    institution_id: str | None = None,
) -> str:
    sec = sector_slug(sector)
    if institution_id:
        return f"MedBand-{sec}-{institution_id}-{case_id}"
    return f"MedBand-{sec}-{case_id}"
