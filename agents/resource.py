"""Resource Agent - Phase 1 run() + Phase 2 Band listener."""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from agents._band import run_band_agent
from agents._claude import call_claude
from agents._mock import mock_resource
from core.audit_log import post
from core.sector_loader import load_prompt, load_resource_data_for


def _resource_payload(
    case_id: str,
    requested_service: str,
    intake_result: dict | None,
) -> dict:
    resource_data = load_resource_data_for(requested_service, intake_result)
    return {
        "case_id": case_id,
        "requested_service": requested_service,
        "intake": intake_result or {},
        **resource_data,
    }


def run(case_id: str, requested_service: str, intake_result: dict = None) -> dict:
    """Phase 1 direct-call path (preserved for workflow.py / Flask form)."""
    system_prompt = load_prompt("resource")
    user_msg = json.dumps(_resource_payload(case_id, requested_service, intake_result))
    payload = call_claude(
        system_prompt,
        user_msg,
        model="gpt-4o-mini",
        mock_fn=lambda: mock_resource(requested_service, intake_result or {}),
    )
    payload["case_id"] = case_id
    post("resource", payload.get("status", "RESOURCE_COMPLETE"), case_id, payload)
    # SUI_MODE: persist this agent's output to Walrus and attach the blob id.
    # No-op on the default Band path.
    if os.environ.get("SUI_MODE", "false").strip().lower() == "true":
        from core.walrus_client import store_stage_payload

        payload["walrus_blob_id"] = store_stage_payload(case_id, "resource", payload)
    return payload


def _band_prompt() -> str:
    """Band system prompt — inventory data is injected per request, not at startup."""
    return (
        load_prompt("resource")
        + "\n\n## Sector Resource Data\n"
        + "Do NOT expect full inventory data in this system prompt. "
        + "Use only the relevant entries included in each RESOURCE_REQUEST message. "
        + "Send exactly ONE band_send_message per case containing JSON only. "
        + "Use institution_name and requested_service from the case payload, not invented values. "
        + "Never send a second summary message, --- blocks, or legacy templates like 'Resource confirmed'. "
        + "Post one clean human-readable RESOURCE COMPLETE message via band_send_message. "
        + "Never post raw JSON. Only respond to the Coordinator. "
        + "Never message Verification directly.\n"
    )


async def main():
    await run_band_agent(
        "resource",
        _band_prompt(),
        "MedBand Resource Agent connected to Band",
    )


if __name__ == "__main__":
    asyncio.run(main())
