"""Resource Agent - checks stock, beds, slots, and availability."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents._claude import call_claude
from agents._mock import mock_resource
from core.audit_log import post
from core.sector_loader import load_prompt, load_resource_data


def run(case_id: str, requested_service: str, intake_result: dict = None) -> dict:
    system_prompt = load_prompt("resource")
    resource_data = load_resource_data()
    user_msg = json.dumps(
        {
            "case_id": case_id,
            "requested_service": requested_service,
            "intake": intake_result or {},
            **resource_data,
        }
    )
    payload = call_claude(
        system_prompt,
        user_msg,
        model="claude-haiku-4-5",
        mock_fn=lambda: mock_resource(requested_service, intake_result or {}),
    )
    payload["case_id"] = case_id
    post("resource", payload.get("status", "RESOURCE_COMPLETE"), case_id, payload)
    return payload


if __name__ == "__main__":
    print("Resource agent module loaded - no errors")
