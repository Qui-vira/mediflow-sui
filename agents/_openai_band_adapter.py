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


def _patch_orphaned_tool_calls(messages: OpenAIMessages) -> None:
    """Inject synthetic tool results for assistant tool_calls missing responses."""
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg.get("role") != "assistant":
            i += 1
            continue

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            if msg.get("content") is None:
                msg["content"] = ""
            i += 1
            continue

        call_ids = {tc["id"] for tc in tool_calls if tc.get("id")}
        j = i + 1
        matched_ids: set[str] = set()
        while j < len(messages) and messages[j].get("role") == "tool":
            tool_call_id = messages[j].get("tool_call_id")
            if tool_call_id in call_ids:
                matched_ids.add(tool_call_id)
            j += 1

        orphaned_ids = call_ids - matched_ids
        if orphaned_ids:
            logger.warning(
                "Patching %d orphaned OpenAI tool_call(s): %s",
                len(orphaned_ids),
                sorted(orphaned_ids),
            )
            synthetic = [
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": "Error: tool execution was interrupted",
                }
                for tool_id in sorted(orphaned_ids)
            ]
            messages[i + 1 : i + 1] = synthetic
            i += len(synthetic)

        i += 1


def _sanitize_openai_messages(messages: OpenAIMessages) -> OpenAIMessages:
    """Remove or repair message sequences AIML rejects."""
    sanitized: OpenAIMessages = []

    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            if sanitized and sanitized[-1].get("role") == "assistant":
                prior_calls = sanitized[-1].get("tool_calls") or []
                tool_call_id = msg.get("tool_call_id")
                if any(tc.get("id") == tool_call_id for tc in prior_calls):
                    sanitized.append(msg)
                    continue
            logger.warning(
                "Dropping orphaned tool message (tool_call_id=%s)",
                msg.get("tool_call_id"),
            )
            sanitized.append(
                {
                    "role": "user",
                    "content": f"[Tool result]: {msg.get('content', '')}",
                }
            )
            continue

        if role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content")
            if not tool_calls and content is None:
                logger.warning("Repairing assistant message with null content")
                msg = {**msg, "content": ""}

        sanitized.append(msg)

    _patch_orphaned_tool_calls(sanitized)
    return sanitized


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
        return _sanitize_openai_messages(messages)


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
            self._message_history[room_id] = (
                _sanitize_openai_messages(list(history)) if history else []
            )
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

        api_messages = _sanitize_openai_messages(self._message_history[room_id])

        while True:
            try:
                request_kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt},
                        *api_messages,
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.3,
                }
                if tool_schemas:
                    request_kwargs["tools"] = tool_schemas
                response = await self.client.chat.completions.create(**request_kwargs)
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
                    api_messages.append({"role": "assistant", "content": content})
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

            assistant_entry = {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": serialized_calls,
            }
            self._message_history[room_id].append(assistant_entry)
            api_messages.append(assistant_entry)

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

                tool_entry = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_str,
                }
                self._message_history[room_id].append(tool_entry)
                api_messages.append(tool_entry)

    async def on_cleanup(self, room_id: str) -> None:
        self._message_history.pop(room_id, None)

    async def _report_error(self, tools: AgentToolsProtocol, error: str) -> None:
        try:
            await tools.send_event(content=f"Error: {error}", message_type="error")
        except Exception as exc:
            logger.warning("Failed to send error event: %s", exc)
