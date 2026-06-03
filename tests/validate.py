"""MedBand Phase 1 validation script — run all checklist checks."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SECTORS = ["pharmacy", "hospital_triage", "lab", "mental_health", "hmo_claims", "emergency"]


def validate_json_files():
    errors = []
    for sector in SECTORS:
        data_dir = ROOT / "data" / sector
        for f in data_dir.glob("*.json"):
            try:
                json.load(open(f, encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{f}: {exc}")
    return errors


def validate_prompts():
    errors = []
    agents = ["coordinator", "intake", "verification", "resource"]
    for sector in SECTORS:
        for agent in agents:
            path = ROOT / "prompts" / sector / f"{agent}.md"
            if not path.exists():
                errors.append(f"Missing prompt: {path}")
    return errors


def test_pipeline():
    from core.audit_log import clear
    from core.workflow import run_case

    clear()
    result = run_case(
        "Name: Ada. Issue: fever and headache. Requested service: Amoxicillin. Urgency: high"
    )
    audit_count = len(result.get("audit_trail", []))
    if audit_count < 5:
        return [f"Expected >= 5 audit entries, got {audit_count}"]
    if result.get("status") not in ("READY_FOR_REVIEW", "ESCALATED", "INCOMPLETE"):
        return [f"Unexpected status: {result.get('status')}"]
    if not result.get("human_role"):
        return ["Missing human_role in summary"]
    return []


def test_escalation():
    from core.audit_log import clear
    from core.workflow import run_case

    clear()
    result = run_case("Name: Test. Issue: insomnia. Requested service: Rohypnol. Urgency: high")
    if result.get("status") != "ESCALATED":
        return [f"Expected ESCALATED for banned drug, got {result.get('status')}"]
    agents = [e["agent"] for e in result.get("audit_trail", [])]
    if "resource" in agents:
        return ["Resource agent should be skipped on escalation"]
    if not any(e.get("status") == "HUMAN_ALERT" for e in result.get("audit_trail", [])):
        return ["Expected HUMAN_ALERT in audit trail"]
    return []


def main():
    print("MedBand Phase 1 Validation")
    print("=" * 40)
    all_errors = []

    print("\n[1/4] Validating JSON files...")
    errs = validate_json_files()
    print(f"  {'PASS' if not errs else 'FAIL'} ({len(list((ROOT / 'data').rglob('*.json')))} files)")
    all_errors.extend(errs)

    print("\n[2/4] Validating prompt files...")
    errs = validate_prompts()
    print(f"  {'PASS' if not errs else 'FAIL'} (24 prompts expected)")
    all_errors.extend(errs)

    print("\n[3/4] Pipeline test (Claude API)...")
    try:
        errs = test_pipeline()
        print(f"  {'PASS' if not errs else 'FAIL'}")
        all_errors.extend(errs)
    except Exception as exc:
        print(f"  FAIL: {exc}")
        all_errors.append(str(exc))

    print("\n[4/4] Escalation test (banned drug)...")
    try:
        errs = test_escalation()
        print(f"  {'PASS' if not errs else 'FAIL'}")
        all_errors.extend(errs)
    except Exception as exc:
        print(f"  FAIL: {exc}")
        all_errors.append(str(exc))

    print("\n" + "=" * 40)
    if all_errors:
        print(f"FAILED — {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
