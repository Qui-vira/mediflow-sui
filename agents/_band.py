"""Shared Band SDK 1.0.0 bootstrap for MedBand Phase 2 agents."""
import os

from band import Agent
from band.core.types import AdapterFeatures, Emit
from dotenv import load_dotenv

from agents._aiml import AIML_BASE_URL, DEFAULT_MODEL
from agents._openai_band_adapter import AimlOpenAIAdapter

load_dotenv()

BAND_MODEL = os.getenv("AIML_MODEL", DEFAULT_MODEL)


def resolve_sector_from_message(message: dict | None = None) -> str:
    """Read sector from Band message payload; fall back to ACTIVE_SECTOR env."""
    if message:
        if isinstance(message.get("sector"), str):
            return message["sector"]
        for key in ("payload", "data", "case_payload", "content"):
            nested = message.get(key)
            if isinstance(nested, dict) and nested.get("sector"):
                return nested["sector"]
    return os.getenv("ACTIVE_SECTOR", "pharmacy")


def apply_sector_from_message(message: dict | None = None) -> str:
    """Set thread-local sector context from an incoming Band message."""
    from core.sector_loader import set_active_sector

    sector = resolve_sector_from_message(message)
    set_active_sector(sector)
    return sector


def get_agent_credentials(agent_name: str) -> tuple[str, str]:
    """Load Band credentials from agent_config.yaml (local) or env vars (Railway)."""
    try:
        from band.config import load_agent_config

        return load_agent_config(agent_name)
    except (FileNotFoundError, KeyError, ValueError):
        env_prefix = agent_name.upper()
        agent_id = os.environ.get(f"{env_prefix}_AGENT_ID")
        api_key_val = os.environ.get(f"{env_prefix}_API_KEY")
        if not agent_id or not api_key_val:
            raise ValueError(
                f"No credentials for {agent_name}. "
                f"Set {env_prefix}_AGENT_ID and {env_prefix}_API_KEY env vars."
            )
        return agent_id, api_key_val


def build_adapter(prompt: str) -> AimlOpenAIAdapter:
    """Build AI/ML API adapter with execution reporting enabled."""
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        raise ValueError("AIML_API_KEY is not configured.")
    return AimlOpenAIAdapter(
        model=BAND_MODEL,
        prompt=prompt,
        api_key=api_key,
        base_url=AIML_BASE_URL,
        features=AdapterFeatures(emit=frozenset({Emit.EXECUTION})),
    )


def create_band_agent(agent_name: str, prompt: str) -> Agent:
    agent_id, api_key = get_agent_credentials(agent_name)
    return Agent.create(
        adapter=build_adapter(prompt),
        agent_id=agent_id,
        api_key=api_key,
    )


async def run_band_agent(agent_name: str, prompt: str, connected_message: str):
    agent = create_band_agent(agent_name, prompt)
    print(connected_message)
    await agent.run()
