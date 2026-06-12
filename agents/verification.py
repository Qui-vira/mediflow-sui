"""Verification Agent - Phase 1 run() + Phase 2 Band listener."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from agents._band import run_band_agent
from agents._claude import call_claude
from agents._mock import mock_verification
from core.audit_log import post
from core.sector_loader import load_prompt, load_verification_data


def run(case_id: str, requested_service: str, intake_result: dict = None) -> dict:
    """Phase 1 direct-call path (preserved for workflow.py / Flask form)."""
    system_prompt = load_prompt("verification")
    verification_data = load_verification_data()
    user_msg = json.dumps(
        {
            "case_id": case_id,
            "requested_service": requested_service,
            "intake": intake_result or {},
            **verification_data,
        }
    )
    payload = call_claude(
        system_prompt,
        user_msg,
        model="claude-sonnet-4-5",
        mock_fn=lambda: mock_verification(requested_service, intake_result or {}),
    )
    payload["case_id"] = case_id
    post("verification", payload.get("status", "CASE_CLEAR"), case_id, payload)
    return payload


def _band_prompt() -> str:
    system_prompt = load_prompt("verification")
    verification_data = load_verification_data()
    return system_prompt + f"\n\n## Sector Verification Data\n{json.dumps(verification_data, indent=2)}\n"


async def main():
    await run_band_agent(
        "verification",
        _band_prompt(),
        "MedBand Verification Agent connected to Band",
    )


if __name__ == "__main__":
    asyncio.run(main())
