"""Patient-facing reports and decision persistence."""
from core.sector_loader import human_role


def build_patient_report(case: dict) -> dict:
    case_id = case.get("case_id", "UNKNOWN")
    intake = case.get("intake", {})
    verification = case.get("verification", {})
    resource = case.get("resource", {})
    decision = case.get("decision", {})
    status = case.get("status", "UNKNOWN")
    name = intake.get("requester_name") or intake.get("caller_name") or "Requester"
    service = intake.get("requested_service", "")

    lines = [
        f"MedBand Case Report - {case_id}",
        f"Patient/Caller: {name}",
        f"Service requested: {service}",
        f"Processing status: {status.replace('_', ' ').title()}",
    ]

    if verification.get("reason"):
        lines.append(f"Verification: {verification['reason']}")
    if resource:
        if resource.get("in_stock") is True:
            lines.append(f"Availability: In stock ({resource.get('quantity_available', '?')} units)")
        elif resource.get("in_stock") is False:
            lines.append("Availability: Out of stock")
        if resource.get("unit_price_ngn"):
            lines.append(f"Estimated price: NGN {resource['unit_price_ngn']:,}")

    if decision:
        d = decision.get("decision", "").replace("_", " ").title()
        lines.append(f"Final decision: {d} by {decision.get('by', human_role())}")
        if decision.get("notes"):
            lines.append(f"Notes: {decision['notes']}")
    else:
        lines.append(f"Awaiting review by {case.get('human_role', human_role())}.")

    lines.append("AI agents do not prescribe or approve. A human professional makes the final decision.")

    return {
        "case_id": case_id,
        "headline": _headline(case, decision),
        "summary_lines": lines,
        "report_text": "\n".join(lines),
        "has_decision": bool(decision),
    }


def _headline(case: dict, decision: dict) -> str:
    if decision:
        d = decision.get("decision", "")
        if d == "APPROVED":
            return "Your case has been approved."
        if d == "REJECTED":
            return "Your case was not approved."
        if d == "MORE_INFO_REQUESTED":
            return "More information is needed."
    status = case.get("status", "")
    if status == "ESCALATED":
        return "Your case requires urgent human review."
    if status == "READY_FOR_REVIEW":
        return "Your case is being reviewed."
    if status == "INCOMPLETE":
        return "Your case is incomplete."
    return "Case update available."
