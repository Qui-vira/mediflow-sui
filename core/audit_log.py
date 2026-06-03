"""Phase 1 mock Band room. Phase 2: replace post() with Band SDK send_message()."""
from datetime import datetime, timezone

_log = []


def post(agent: str, status: str, case_id: str, data: dict):
    entry = {
        "agent": agent,
        "status": status,
        "case_id": case_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }
    _log.append(entry)
    print(f"[AUDIT] {agent} -> {status} | case: {case_id}")
    return entry


def get_log(case_id: str = None):
    if case_id:
        return [e for e in _log if e["case_id"] == case_id]
    return list(_log)


def clear():
    _log.clear()
