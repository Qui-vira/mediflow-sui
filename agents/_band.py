"""Shared Band SDK bootstrap for MedBand Phase 2 agents."""
import asyncio

from dotenv import load_dotenv
from thenvoi import Agent
from thenvoi.adapters import AnthropicAdapter
from thenvoi.config import load_agent_config

load_dotenv()

BAND_MODEL = "claude-sonnet-4-6"


def build_adapter(custom_section: str) -> AnthropicAdapter:
    return AnthropicAdapter(
        model=BAND_MODEL,
        custom_section=custom_section,
        enable_execution_reporting=True,
    )


def create_band_agent(agent_name: str, custom_section: str) -> Agent:
    agent_id, api_key = load_agent_config(agent_name)
    adapter = build_adapter(custom_section)
    return Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)


async def run_band_agent(agent_name: str, custom_section: str, connected_message: str):
    agent = create_band_agent(agent_name, custom_section)
    print(connected_message)
    await agent.run()
