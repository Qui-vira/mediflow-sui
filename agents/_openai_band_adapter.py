"""OpenAI-compatible Band adapter for AI/ML API."""
from __future__ import annotations

import json
import logging
from typing import Any, ClassVar

from openai import AsyncOpenAI

from band.converters._tool_parsing import parse_tool_call, parse_tool_result
from band.core.protocols import AgentToolsProtocol, HistoryConverter
from band.core.simple_adapter import SimpleAdapter
from band.core.types import AdapterFeatures, Capability, Emit, PlatformMessage
from band.runtime.prompts import render_system_prompt

logger = logging.getLogger(__name__)

OpenAIMessages = list[dict[str, Any]]


class OpenAIHistoryConverter(HistoryConverter[OpenAIMessages]):
    """Convert Band platform history to OpenAI chat message format."""

    def __init__(self, agent_name: str = ""):
        self._agent_name = agent_name

    def set_agent_name(self, name: str) -> None:
        self._agent_name = name

    def convert(self, raw: list[dict[str, Any]]) -> OpenAIMessages:
        messages: OpenAIMessages = []
        pending_tool_calls: list[dict[str, Any]] = []
        pending_tool_results: list[dict[str, Any]] = []

        def flush_tool_calls() -> None:
            if not pending_tool_calls:
                return
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": pending_tool_calls.copy(),
                }
            )
            pending_tool_calls.clear()

        def flush_tool_results() -> None:
            if not pending_tool_results:
                return
            messages.extend(pending_tool_results)
            pending_tool_results.clear()

        for hist in raw:
            message_type = hist.get("message_type", "text")
            content = hist.get("content", "")

            if message_type == "tool_call":
                flush_tool_results()
                parsed = parse_tool_call(content)
                if parsed:
                    pending_tool_calls.append(
                        {
                            "id": parsed.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": parsed.name,
                                "arguments": json.dumps(parsed.args),
                            },
                        }
                    )
            elif message_type == "tool_result":
                flush_tool_calls()
                parsed = parse_tool_result(content)
                if parsed:
                    pending_tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": parsed.tool_call_id,
                            "content": (
                                parsed.output
                                if isinstance(parsed.output, str)
                                else json.dumps(parsed.output, default=str)
                            ),
                        }
                    )
            elif message_type == "text":
                flush_tool_calls()
                flush_tool_results()
                role = hist.get("role", "user")
                sender_name = hist.get("sender_name", "")
                if role == "assistant" and sender_name == self._agent_name:
                    continue
                messages.append(
                    {
                        "role": "user",
                        "content": f"[{sender_name}]: {content}"
                        if sender_name
                        else content,
                    }
                )

        flush_tool_calls()
        flush_tool_results()
        return messages


class AimlOpenAIAdapter(SimpleAdapter[OpenAIMessages]):
    """Band adapter backed by AI/ML API (OpenAI-compatible)."""

    SUPPORTED_EMIT: ClassVar[frozenset[Emit]] = frozenset({Emit.EXECUTION})
    SUPPORTED_CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset(
        {Capability.MEMORY, Capability.CONTACTS}
    )

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        prompt: str | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.aimlapi.com/v1",
        max_tokens: int = 4096,
        features: AdapterFeatures | None = None,
    ):
        super().__init__(
            history_converter=OpenAIHistoryConverter(),
            features=features,
        )
        self.model = model
        self._prompt = prompt
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._message_history: dict[str, list[dict[str, Any]]] = {}
        self._system_prompt = ""

    async def on_started(self, agent_name: str, agent_description: str) -> None:
        await super().on_started(agent_name, agent_description)
        self._system_prompt = render_system_prompt(
            agent_name=agent_name,
            agent_description=agent_description,
            custom_section=self._prompt or "",
            features=self.features,
        )
        logger.info("AIML OpenAI adapter started for agent: %s", agent_name)

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: OpenAIMessages,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        if is_session_bootstrap:
            self._message_history[room_id] = list(history) if history else []
        elif room_id not in self._message_history:
            self._message_history[room_id] = []

        if participants_msg:
            self._message_history[room_id].append(
                {"role": "user", "content": f"[System]: {participants_msg}"}
            )
        if contacts_msg:
            self._message_history[room_id].append(
                {"role": "user", "content": f"[System]: {contacts_msg}"}
            )

        self._message_history[room_id].append(
            {"role": "user", "content": msg.format_for_llm()}
        )

        include_memory = Capability.MEMORY in self.features.capabilities
        include_contacts = Capability.CONTACTS in self.features.capabilities
        tool_schemas = tools.get_openai_tool_schemas(
            include_memory=include_memory,
            include_contacts=include_contacts,
        )

        while True:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        *self._message_history[room_id],
                    ],
                    tools=tool_schemas or None,
                    max_tokens=self.max_tokens,
                    temperature=0.3,
                )
            except Exception as exc:
                logger.error("Error calling AIML API: %s", exc, exc_info=True)
                await self._report_error(tools, str(exc))
                raise

            choice = response.choices[0]
            assistant_message = choice.message
            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                content = assistant_message.content or ""
                if content:
                    self._message_history[room_id].append(
                        {"role": "assistant", "content": content}
                    )
                break

            serialized_calls = []
            for tool_call in tool_calls:
                serialized_calls.append(
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                )

            self._message_history[room_id].append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": serialized_calls,
                }
            )

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments or "{}")
                tool_call_id = tool_call.id

                if Emit.EXECUTION in self.features.emit:
                    try:
                        await tools.send_event(
                            content=json.dumps(
                                {
                                    "name": tool_name,
                                    "args": tool_input,
                                    "tool_call_id": tool_call_id,
                                }
                            ),
                            message_type="tool_call",
                        )
                    except Exception as exc:
                        logger.warning("Failed to send tool_call event: %s", exc)

                try:
                    result = await tools.execute_tool_call(tool_name, tool_input)
                    result_str = (
                        json.dumps(result, default=str)
                        if not isinstance(result, str)
                        else result
                    )
                    is_error = False
                except Exception as exc:
                    result_str = f"Error: {exc}"
                    is_error = True
                    logger.error("Tool %s failed: %s", tool_name, exc)

                if Emit.EXECUTION in self.features.emit:
                    try:
                        await tools.send_event(
                            content=json.dumps(
                                {
                                    "name": tool_name,
                                    "output": result_str,
                                    "tool_call_id": tool_call_id,
                                    "is_error": is_error,
                                }
                            ),
                            message_type="tool_result",
                        )
                    except Exception as exc:
                        logger.warning("Failed to send tool_result event: %s", exc)

                self._message_history[room_id].append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str,
                    }
                )

    async def on_cleanup(self, room_id: str) -> None:
        self._message_history.pop(room_id, None)

    async def _report_error(self, tools: AgentToolsProtocol, error: str) -> None:
        try:
            await tools.send_event(content=f"Error: {error}", message_type="error")
        except Exception as exc:
            logger.warning("Failed to send error event: %s", exc)
