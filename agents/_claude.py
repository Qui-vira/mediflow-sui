"""Shared Claude API helper for MedBand agents."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

_client = None
_use_mock = None


def _should_mock() -> bool:
    global _use_mock
    if _use_mock is None:
        key = os.getenv("ANTHROPIC_API_KEY", "")
        _use_mock = not key or key.startswith("your-") or key == "sk-placeholder"
        if _use_mock:
            print("[MedBand] No valid ANTHROPIC_API_KEY - using mock agent responses")
    return _use_mock


def get_client():
    from anthropic import Anthropic

    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"raw": text, "parse_error": True}


def call_claude(system_prompt: str, user_msg: str, model: str = "claude-haiku-4-5", mock_fn=None) -> dict:
    if _should_mock() and mock_fn:
        return mock_fn()

    response = get_client().messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = response.content[0].text
    return extract_json(text)
