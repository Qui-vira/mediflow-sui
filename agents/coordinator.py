"""
Coordinator Agent - Phase 1 runs via core/workflow.py (direct function calls).
Phase 2: this file becomes a persistent Band agent (see Phase 2 Band Wiring Guide).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    print("MedBand Coordinator - Phase 1")
    print("In Phase 1, the coordinator runs inside core/workflow.py.")
    print("Run: python main.py  OR  python frontend/app.py")
    print("Phase 2: this process connects to Band as a persistent agent.")


if __name__ == "__main__":
    main()
