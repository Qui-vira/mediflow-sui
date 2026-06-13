"""Shared Band SDK 1.0.0 bootstrap for MedBand Phase 2 agents."""
import os

from band import Agent
from band.adapters import AnthropicAdapter
from band.core.types import AdapterFeatures, Emit
from dotenv import load_dotenv

load_dotenv()

BAND_MODEL = "claude-sonnet-4-6"


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


def build_adapter(prompt: str) -> AnthropicAdapter:
    """Build Anthropic adapter with execution reporting enabled."""
    return AnthropicAdapter(
        model=BAND_MODEL,
        prompt=prompt,
        provider_key=os.getenv("ANTHROPIC_API_KEY"),
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
