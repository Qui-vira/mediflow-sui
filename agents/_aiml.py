"""AI/ML API client (OpenAI-compatible) for MedBand Phase 1 agents."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

AIML_BASE_URL = os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1")
DEFAULT_MODEL = os.getenv("AIML_MODEL", "gpt-4o-mini")

_client = None
_use_mock = None


def get_api_key() -> str:
    return os.getenv("AIML_API_KEY", "")


def _should_mock() -> bool:
    global _use_mock
    if _use_mock is None:
        key = get_api_key()
        _use_mock = not key or key.startswith("your-") or key == "sk-placeholder"
        if _use_mock:
            print("[MedBand] No valid AIML_API_KEY - using mock agent responses")
    return _use_mock


def create_aiml_client():
    from openai import OpenAI

    return OpenAI(
        api_key=get_api_key(),
        base_url=AIML_BASE_URL,
    )


def get_client():
    global _client
    if _client is None:
        _client = create_aiml_client()
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


def call_aiml(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    mock_fn=None,
    max_tokens: int = 2000,
) -> dict:
    if _should_mock() and mock_fn:
        return mock_fn()

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    text = response.choices[0].message.content or ""
    return extract_json(text)


def call_aiml_text(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2000,
) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""
