"""Coordinator Agent - Phase 2 Band persistent process."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from agents._band import run_band_agent
from core.sector_loader import load_prompt


async def main():
    system_prompt = load_prompt("coordinator")
    await run_band_agent(
        "coordinator",
        system_prompt,
        "MedBand Coordinator connected to Band",
    )


if __name__ == "__main__":
    asyncio.run(main())
