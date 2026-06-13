"""Shared LLM helper for MedBand Phase 1 agents (AI/ML API)."""
from agents._aiml import call_aiml, extract_json

__all__ = ["call_aiml", "call_claude", "extract_json"]


def call_claude(system_prompt: str, user_msg: str, model: str = "gpt-4o-mini", mock_fn=None) -> dict:
    """Backward-compatible alias for Phase 1 workflow callers."""
    return call_aiml(system_prompt, user_msg, model=model, mock_fn=mock_fn)
