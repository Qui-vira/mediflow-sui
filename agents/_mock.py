"""Rule-based mock responses when ANTHROPIC_API_KEY is not configured."""
import re

from core.sector_loader import ACTIVE_SECTOR, load_verification_data, load_resource_data


def _parse_raw(raw: str) -> dict:
    fields = {}
    text = raw.replace("\n", ". ")
    parts = re.split(r"\.\s*(?=[A-Za-z][^:]*:)", text)
    for part in parts:
        part = part.strip().rstrip(".")
        if ":" in part:
            key, _, val = part.partition(":")
            fields[key.strip().lower()] = val.strip()
    return fields


def mock_intake(raw_input: str) -> dict:
    fields = _parse_raw(raw_input)
    name = fields.get("name", fields.get("patient", "Unknown"))
    service = fields.get(
        "requested service",
        fields.get("service", fields.get("drug", fields.get("test", ""))),
    )
    issue = fields.get("issue", "")
    urgency = fields.get("urgency", "medium").lower()

    if not name or not service:
        missing = []
        if not name:
            missing.append("requester_name")
        if not service:
            missing.append("requested_service")
        return {"status": "INTAKE_INCOMPLETE", "missing_fields": missing}

    base = {
        "status": "INTAKE_COMPLETE",
        "requester_name": name,
        "requested_service": service,
        "urgency": urgency,
    }

    if ACTIVE_SECTOR == "pharmacy":
        base["presenting_issue"] = issue
    elif ACTIVE_SECTOR == "hospital_triage":
        base["chief_complaint"] = issue or service
        base["vitals_description"] = ""
    elif ACTIVE_SECTOR == "lab":
        base["test_requested"] = service
        base["referral_number"] = fields.get("referral", "REF-001")
        base["patient_id"] = fields.get("patient id", "PAT-001")
    elif ACTIVE_SECTOR == "mental_health":
        base["presenting_concern"] = issue or service
        base["duration"] = "2 weeks"
        harm = "yes" if re.search(r"self.?harm|suicid|kill myself", issue, re.I) else "no"
        base["self_harm_flag"] = harm
    elif ACTIVE_SECTOR == "hmo_claims":
        base["procedure_code"] = service
        base["policy_number"] = fields.get("policy", "HMO-2024-001")
        base["provider_name"] = fields.get("provider", "General Hospital Lagos")
    elif ACTIVE_SECTOR == "emergency":
        base["emergency_type"] = service
        base["location"] = fields.get("location", "Lagos")
        base["caller_name"] = name
        base["additional_details"] = issue

    return base


def mock_verification(requested_service: str, intake_result: dict) -> dict:
    service = requested_service.lower()
    data = load_verification_data()

    if ACTIVE_SECTOR == "pharmacy":
        registry = data.get("registry", {})
        drugs = {d["drug_name"].lower(): d for d in registry.get("drugs", [])}
        drug = drugs.get(service)
        if not drug:
            for name, info in drugs.items():
                if name in service or service in name:
                    drug = info
                    break
        if not drug:
            return {"status": "CASE_ESCALATE", "drug_name": requested_service, "reason": "Drug not in NAFDAC registry", "registry_status": "not_found"}
        status_val = drug["status"]
        if status_val == "banned":
            return {"status": "CASE_ESCALATE", "drug_name": drug["drug_name"], "registry_status": "banned", "reason": "Drug is banned by NAFDAC"}
        if status_val == "suspended":
            return {"status": "CASE_ESCALATE", "drug_name": drug["drug_name"], "registry_status": "suspended", "reason": "Drug is suspended by NAFDAC"}
        risk = data.get("risk_table", {})
        interactions = [i for i in risk.get("interactions", []) if i["drug_name"].lower() == service or i["interacts_with"].lower() == service]
        critical = [i for i in interactions if i["severity"] == "critical"]
        if critical:
            return {"status": "CASE_ESCALATE", "drug_name": drug["drug_name"], "registry_status": "registered", "interactions_found": critical, "reason": "Critical drug interaction detected"}
        if interactions:
            return {"status": "CASE_CAUTION", "drug_name": drug["drug_name"], "registry_status": "registered", "interactions_found": interactions, "reason": "Medium severity interactions noted"}
        return {"status": "CASE_CLEAR", "drug_name": drug["drug_name"], "registry_status": "registered", "interactions_found": [], "reason": "Registered, no critical interactions"}

    if ACTIVE_SECTOR == "hospital_triage":
        complaint = (intake_result.get("chief_complaint") or service).lower()
        criteria = data.get("triage_criteria", {}).get("rules", [])
        for rule in criteria:
            if any(kw in complaint for kw in rule["symptom_keywords"]):
                level = rule["triage_level"]
                if level == "red":
                    return {"status": "CASE_ESCALATE", "triage_level": "red", "matched_keywords": rule["symptom_keywords"], "reason": rule["action"]}
                if level == "yellow":
                    return {"status": "CASE_CAUTION", "triage_level": "yellow", "matched_keywords": rule["symptom_keywords"], "reason": rule["action"]}
        return {"status": "CASE_CLEAR", "triage_level": "green", "matched_keywords": [], "reason": "Non-urgent, standard queue"}

    if ACTIVE_SECTOR == "mental_health":
        if intake_result.get("self_harm_flag") == "yes":
            return {"status": "CASE_ESCALATE", "risk_level": "critical", "flags_matched": ["self_harm"], "reason": "Self-harm flag - immediate human response"}
        concern = (intake_result.get("presenting_concern") or service).lower()
        for rule in data.get("criteria", []):
            if any(kw in concern for kw in rule.get("keyword_flags", [])):
                level = rule["risk_level"]
                if level in ("critical", "high"):
                    return {"status": "CASE_ESCALATE", "risk_level": level, "flags_matched": rule["keyword_flags"], "reason": rule["action"]}
                if level == "medium":
                    return {"status": "CASE_CAUTION", "risk_level": level, "flags_matched": rule["keyword_flags"], "reason": rule["action"]}
        return {"status": "CASE_CLEAR", "risk_level": "low", "flags_matched": [], "reason": "Standard intake pathway"}

    if ACTIVE_SECTOR == "emergency":
        etype = (intake_result.get("emergency_type") or service).lower()
        for rule in data.get("rules", []):
            if rule["emergency_type"] in etype or any(kw in etype for kw in rule.get("keywords", [])):
                sev = rule["severity_level"]
                if sev == "P1":
                    return {"status": "CASE_ESCALATE", "severity_level": "P1", "protocol": rule["protocol"], "reason": "Life-threatening emergency"}
                if sev == "P2":
                    return {"status": "CASE_CAUTION", "severity_level": "P2", "protocol": rule["protocol"], "reason": "Priority response required"}
        return {"status": "CASE_CLEAR", "severity_level": "P3", "protocol": "Standard response", "reason": "Low severity"}

    return {"status": "CASE_CLEAR", "reason": f"Verified for {ACTIVE_SECTOR}"}


def mock_resource(requested_service: str, intake_result: dict) -> dict:
    service = requested_service
    data = load_resource_data()

    if ACTIVE_SECTOR == "pharmacy":
        inventory = data.get("resources", {}).get("inventory", [])
        for item in inventory:
            if item["drug_name"].lower() == service.lower():
                return {
                    "status": "RESOURCE_COMPLETE",
                    "drug_name": item["drug_name"],
                    "in_stock": item["quantity_available"] > 0,
                    "quantity_available": item["quantity_available"],
                    "unit_price_ngn": item["unit_price_ngn"],
                    "form": item["form"],
                    "strength": item["strength"],
                }
        return {"status": "RESOURCE_COMPLETE", "drug_name": service, "in_stock": False, "quantity_available": 0, "notes": "Not in inventory"}

    if ACTIVE_SECTOR == "hospital_triage":
        beds = data.get("beds", {}).get("wards", [])
        best = max(beds, key=lambda w: w["beds_available"]) if beds else {}
        return {"status": "RESOURCE_COMPLETE", "recommended_ward": best.get("ward_name", ""), "beds_available": best.get("beds_available", 0), "next_available": best.get("next_available", "")}

    if ACTIVE_SECTOR == "lab":
        slots = data.get("lab_slots", {}).get("slots", [])
        for slot in slots:
            if slot["test_name"].lower() == service.lower():
                return {"status": "RESOURCE_COMPLETE", **slot}
        return {"status": "RESOURCE_COMPLETE", "test_name": service, "slots_today": 0, "next_available_date": "unknown"}

    if ACTIVE_SECTOR == "mental_health":
        therapists = data.get("therapist_availability", {}).get("therapists", [])
        t = therapists[0] if therapists else {}
        return {"status": "RESOURCE_COMPLETE", "matched_therapist": t.get("therapist_name", ""), "specialty": t.get("specialty", ""), "next_slot": t.get("next_slot", ""), "modality": t.get("modality", "")}

    if ACTIVE_SECTOR == "emergency":
        units = data.get("units", {}).get("units", [])
        available = [u for u in units if u["status"] == "available"]
        nearest = min(available, key=lambda u: u["eta_minutes"]) if available else {}
        return {"status": "RESOURCE_COMPLETE", "assigned_units": [nearest.get("unit_id", "")], "nearest_unit": nearest.get("unit_id", ""), "eta_minutes": nearest.get("eta_minutes", 0)}

    return {"status": "RESOURCE_COMPLETE", "notes": f"Resource check complete for {ACTIVE_SECTOR}"}
