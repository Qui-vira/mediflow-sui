#!/usr/bin/env python3
"""List or clear Band rooms disabled due to message limits."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from core.case_state import clear_disabled_rooms, enable_room, init_case_state, list_disabled_rooms


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage MedBand disabled Band rooms")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List disabled rooms from Postgres/SQLite")

    clear_cmd = sub.add_parser("clear", help="Re-enable one room or all rooms")
    clear_cmd.add_argument("room_id", nargs="?", help="Room ID to re-enable (omit to clear all)")
    clear_cmd.add_argument(
        "--all",
        action="store_true",
        help="Clear every disabled room (same as clear with no room_id)",
    )

    args = parser.parse_args()
    init_case_state()

    if args.command == "list":
        rows = list_disabled_rooms()
        if not rows:
            print("No disabled rooms.")
            return 0
        print(json.dumps(rows, indent=2))
        return 0

    if args.command == "clear":
        if args.room_id:
            removed = enable_room(args.room_id)
            if removed:
                print(f"Re-enabled room: {args.room_id}")
            else:
                print(f"Room not in disabled list: {args.room_id}")
            return 0
        count = clear_disabled_rooms()
        print(f"Cleared {count} disabled room(s).")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
