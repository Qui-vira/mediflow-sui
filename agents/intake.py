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


def run(case_id: str, raw_input: str, institution: dict | None = None) -> dict:
    """Phase 1 direct-call path (preserved for workflow.py / Flask form)."""
    system_prompt = load_prompt("intake")
    user_input = raw_input
    if institution:
        user_input = (
            f"Institution ID: {institution.get('id')}\n"
            f"Institution Name: {institution.get('name')}\n"
            f"Institution Location: {institution.get('location', '')}\n\n"
            f"{raw_input}"
        )
    payload = call_claude(
        system_prompt,
        user_input,
        model="claude-haiku-4-5",
        mock_fn=lambda: mock_intake(user_input),
    )
    payload["case_id"] = case_id
    if institution:
        payload["institution_id"] = institution.get("id")
        payload["institution_name"] = institution.get("name")
    post("intake", payload.get("status", "INTAKE_COMPLETE"), case_id, payload)
    return payload


def _band_prompt() -> str:
    """Band system prompt with mandatory two-message rule reinforcement."""
    return (
        load_prompt("intake")
        + "\n\n## Band posting reminder\n"
        + "Always post structured JSON first, then a **separate message** starting with "
        + "`SUMMARY FOR HUMAN REVIEW` in plain English. Never post JSON only.\n"
    )


async def main():
    await run_band_agent(
        "intake",
        _band_prompt(),
        "MedBand Intake Agent connected to Band",
    )


if __name__ == "__main__":
    asyncio.run(main())
