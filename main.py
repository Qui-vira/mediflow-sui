"""MedBand entry point — run pipeline from CLI."""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core.workflow import run_case


def main():
    parser = argparse.ArgumentParser(description="MedBand Phase 1 CLI")
    parser.add_argument("input", nargs="?", default="Patient: Ada. Drug: Amoxicillin. Urgency: high.")
    parser.add_argument("--sector", default=None, help="Override ACTIVE_SECTOR")
    args = parser.parse_args()

    result = run_case(args.input, sector=args.sector)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
