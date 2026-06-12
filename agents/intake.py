"""Intake Agent - Phase 1 run() + Phase 2 Band listener."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from agents._band import run_band_agent
from agents._claude import call_claude
from agents._mock import mock_intake
from core.audit_log import post
from core.sector_loader import load_prompt


def run(case_id: str, raw_input: str) -> dict:
    """Phase 1 direct-call path (preserved for workflow.py / Flask form)."""
    system_prompt = load_prompt("intake")
    payload = call_claude(
        system_prompt,
        raw_input,
        model="claude-haiku-4-5",
        mock_fn=lambda: mock_intake(raw_input),
    )
    payload["case_id"] = case_id
    post("intake", payload.get("status", "INTAKE_COMPLETE"), case_id, payload)
    return payload


async def main():
    """Phase 2 Band persistent agent."""
    system_prompt = load_prompt("intake")
    await run_band_agent(
        "intake",
        system_prompt,
        "MedBand Intake Agent connected to Band",
    )


if __name__ == "__main__":
    asyncio.run(main())
