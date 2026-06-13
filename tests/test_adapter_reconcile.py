"""Unit tests for tool_call/tool_result reconciliation in the Band adapter.

Proves the orphaned-tool-call loop is gone:
- a tool_call id is matched, OR patched, OR dropped - never two of these
- a real result is never dropped when it has a matching assistant tool_call
- a tool_call is never patched when a real result exists anywhere in history
- reconciliation is idempotent: reconcile(reconcile(x)) == reconcile(x)

Run:
  ./venv/Scripts/python.exe -m pytest tests/test_adapter_reconcile.py -q
  ./venv/Scripts/python.exe tests/test_adapter_reconcile.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents._openai_band_adapter import _reconcile_tool_calls, _sanitize_openai_messages

SYNTHETIC = "Error: tool execution was interrupted"


def assistant_call(*ids, content=""):
    return {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": i,
                "type": "function",
                "function": {"name": "band_send_message", "arguments": "{}"},
            }
            for i in ids
        ],
    }


def tool_result(i, content="ok"):
    return {"role": "tool", "tool_call_id": i, "content": content}


def user(text):
    return {"role": "user", "content": text}


def _call_ids(msgs):
    ids = set()
    for m in msgs:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                ids.add(tc["id"])
    return ids


def assert_wellformed(msgs):
    call_ids = _call_ids(msgs)
    # every surviving tool message maps to a real assistant call id
    for m in msgs:
        if m.get("role") == "tool":
            assert m["tool_call_id"] in call_ids, f"orphan tool result survived: {m}"
    # every assistant tool_calls block is immediately followed by its results, in order
    i = 0
    while i < len(msgs):
        m = msgs[i]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            ids = [tc["id"] for tc in m["tool_calls"]]
            following = msgs[i + 1 : i + 1 + len(ids)]
            assert all(f.get("role") == "tool" for f in following), (
                f"missing results after {ids}: {following}"
            )
            assert [f["tool_call_id"] for f in following] == ids, (
                f"result order/ids mismatch: {following} vs {ids}"
            )
            i += 1 + len(ids)
        else:
            i += 1


def _synthetic_ids(msgs):
    return {
        m["tool_call_id"]
        for m in msgs
        if m.get("role") == "tool" and m.get("content") == SYNTHETIC
    }


def _dropped_texts(msgs):
    return [
        m["content"]
        for m in msgs
        if m.get("role") == "user" and str(m.get("content", "")).startswith("[Tool result]:")
    ]


def test_matched_pair_unchanged():
    msgs = [user("hi"), assistant_call("A"), tool_result("A")]
    out = _reconcile_tool_calls([dict(m) for m in msgs])
    assert out == msgs
    assert_wellformed(out)


def test_orphan_call_is_patched_not_dropped():
    out = _reconcile_tool_calls([assistant_call("A")])
    assert_wellformed(out)
    assert _synthetic_ids(out) == {"A"}
    assert _dropped_texts(out) == []


def test_orphan_result_is_dropped_not_patched():
    out = _reconcile_tool_calls([tool_result("Z", "leftover")])
    assert all(m.get("role") != "tool" for m in out)
    assert _synthetic_ids(out) == set()
    assert _dropped_texts(out) == ["[Tool result]: leftover"]


def test_real_result_not_dropped_when_separated():
    out = _reconcile_tool_calls([assistant_call("A"), user("noise"), tool_result("A", "real")])
    assert_wellformed(out)
    assert _synthetic_ids(out) == set()
    assert _dropped_texts(out) == []
    assert any(
        m.get("role") == "tool" and m["tool_call_id"] == "A" and m["content"] == "real"
        for m in out
    )


def test_no_id_both_patched_and_dropped():
    msgs = [assistant_call("A", "B"), tool_result("A", "real"), tool_result("Z", "orphan")]
    out = _reconcile_tool_calls(msgs)
    assert_wellformed(out)
    synth = _synthetic_ids(out)
    assert synth == {"B"}  # A has a real result; B missing -> patched
    assert "A" not in synth and "Z" not in synth
    assert _dropped_texts(out) == ["[Tool result]: orphan"]  # Z has no call -> dropped


def test_multi_call_partial_results():
    out = _reconcile_tool_calls([assistant_call("A", "B"), tool_result("A")])
    assert_wellformed(out)
    assert _synthetic_ids(out) == {"B"}


def test_duplicate_real_result_collapses():
    out = _reconcile_tool_calls(
        [assistant_call("A"), tool_result("A", "real"), tool_result("A", "dup")]
    )
    assert_wellformed(out)
    tools = [m for m in out if m.get("role") == "tool"]
    assert len(tools) == 1 and tools[0]["content"] == "real"


def test_result_before_call_is_reordered():
    out = _reconcile_tool_calls([tool_result("A", "real"), assistant_call("A")])
    assert_wellformed(out)
    assert _synthetic_ids(out) == set()
    assert _dropped_texts(out) == []


def test_assistant_null_content_normalized():
    out = _reconcile_tool_calls([{"role": "assistant", "content": None}])
    assert out == [{"role": "assistant", "content": ""}]


def test_idempotent():
    cases = [
        [user("hi"), assistant_call("A"), tool_result("A")],
        [assistant_call("A")],
        [tool_result("Z", "x")],
        [assistant_call("A"), user("noise"), tool_result("A")],
        [assistant_call("A", "B"), tool_result("A"), tool_result("Z")],
        [tool_result("A"), assistant_call("A")],
    ]
    for c in cases:
        once = _reconcile_tool_calls([dict(m) for m in c])
        twice = _reconcile_tool_calls([dict(m) for m in once])
        assert once == twice, f"not idempotent for {c}"


def test_sanitize_delegates_and_skips_disabled():
    out = _sanitize_openai_messages([assistant_call("A")], room_id=None)
    assert_wellformed(out)
    assert _synthetic_ids(out) == {"A"}


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
