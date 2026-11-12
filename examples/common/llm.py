"""A thin, provider-neutral LLM wrapper used by every example in these notes.

Why a wrapper? So each example works with Anthropic, OpenAI, or the offline
MockLLM without changing a line, and so you can see clearly what each
provider's API looks like underneath. It is deliberately small: read it once
and you will understand exactly what frameworks do for you.

Choose a provider with the LLM_PROVIDER environment variable (see .env.example):

    LLM_PROVIDER=mock        # default: offline, free, deterministic
    LLM_PROVIDER=anthropic   # needs ANTHROPIC_API_KEY
    LLM_PROVIDER=openai      # needs OPENAI_API_KEY and OPENAI_MODEL

The neutral message format
--------------------------
A conversation is a list of plain dicts:

    {"role": "user", "content": "What's the weather in Paris?"}
    {"role": "assistant", "content": "Let me check.", "tool_calls": [ToolCall(...)]}
    {"role": "tool", "tool_call_id": "call_1", "content": "18°C, sunny", "is_error": False}

Tools are described in one format (a name, a description and a JSON Schema),
and converted to each provider's shape for you:

    {"name": "get_weather", "description": "...", "input_schema": {...JSON Schema...}}
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "other"]
Message = dict[str, Any]
ToolSpec = dict[str, Any]

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"
DEFAULT_MAX_TOKENS = 16000

# Models that accept Anthropic's server-side refusal fallback (`fallbacks="default"`).
# If a safety classifier declines a request, the API retries it on a suitable model.
ANTHROPIC_FALLBACK_MODELS = {
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
    "claude-fable-5-1",
    "claude-fable-5-2",
}
ANTHROPIC_FALLBACK_BETA = "server-side-fallback-2026-07-01"


# --------------------------------------------------------------------------- types


@dataclass
class ToolCall:
    """The model asking us to run one tool."""

    id: str
    name: str
    arguments: dict[str, Any]
    error: str | None = None  # set if the provider sent arguments we could not parse


@dataclass
class Usage:
    """Token counts for one model call."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    """One model reply, the same shape for every provider."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = "end_turn"
    usage: Usage = field(default_factory=Usage)
    provider: str = "mock"
    raw: Any = None  # the provider's original response object, for debugging

    def to_message(self) -> Message:
        """The assistant message to append to the conversation history."""
        msg: Message = {"role": "assistant", "content": self.text, "tool_calls": list(self.tool_calls)}
        if self.provider == "anthropic" and self.raw is not None:
            # Replay Anthropic's content blocks unchanged on the next request.
            # They can include thinking blocks, which must be passed back as-is.
            msg["_raw"] = {"provider": "anthropic", "content": self.raw.content}
        return msg


def user(text: str) -> Message:
    """Build a user message."""
    return {"role": "user", "content": text}


def tool_result(tool_call_id: str, content: str, *, is_error: bool = False) -> Message:
    """Build the message that carries a tool's output back to the model."""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content, "is_error": is_error}


class LLM(ABC):
    """Anything that can take a conversation and return the next reply."""

    provider: str = "base"
    model: str = ""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        """Send the conversation and return the model's next reply."""


# --------------------------------------------------------------------------- Anthropic


def to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert neutral messages to the Anthropic Messages API format.

    Tool results become `tool_result` blocks inside a *user* message, and all
    results for one turn go in a single message, as the API expects.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m["role"]
        if role == "assistant":
            raw = m.get("_raw")
            if raw and raw.get("provider") == "anthropic":
                content: Any = raw["content"]
            else:
                content = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
            out.append({"role": "assistant", "content": content})
            continue

        if role == "tool":
            block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": m["tool_call_id"],
                "content": m["content"],
            }
            if m.get("is_error"):
                block["is_error"] = True
            blocks = [block]
        elif role == "user":
            blocks = [{"type": "text", "text": m["content"]}] if isinstance(m["content"], str) else m["content"]
        else:
            raise ValueError(f"Unknown role: {role!r}")

        # Merge consecutive user-side messages (e.g. several tool results) into one.
        if out and out[-1]["role"] == "user":
            prev = out[-1]["content"]
            if isinstance(prev, str):
                prev = [{"type": "text", "text": prev}]
            out[-1]["content"] = prev + list(blocks)
        elif role == "user" and isinstance(m["content"], str):
            out.append({"role": "user", "content": m["content"]})
        else:
            out.append({"role": "user", "content": list(blocks)})
    return out


_ANTHROPIC_STOP: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "model_context_window_exceeded": "max_tokens",
    "refusal": "refusal",
}


def from_anthropic(resp: Any) -> LLMResponse:
    """Convert an Anthropic Message object to an LLMResponse."""
    texts = [b.text for b in resp.content if b.type == "text"]
    calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input)) for b in resp.content if b.type == "tool_use"]
    return LLMResponse(
        text="".join(texts),
        tool_calls=calls,
        stop_reason=_ANTHROPIC_STOP.get(resp.stop_reason or "", "other"),
        usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens),
        provider="anthropic",
        raw=resp,
    )


class AnthropicLLM(LLM):
    """Claude via the official `anthropic` SDK (Messages API)."""

    provider = "anthropic"

    def __init__(self, model: str | None = None, *, client: Any = None, effort: str | None = None) -> None:
        if client is None:
            import anthropic  # imported lazily so mock-only users need not install it

            client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self.client = client
        self.model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        self.effort = effort or os.getenv("ANTHROPIC_EFFORT") or None  # low | medium | high | xhigh | max
        self.use_fallbacks = (
            self.model in ANTHROPIC_FALLBACK_MODELS and os.getenv("ANTHROPIC_FALLBACKS", "on").lower() != "off"
        )

    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": to_anthropic_messages(messages),
        }
        if system:
            params["system"] = system
        if tools:
            params["tools"] = tools  # our neutral tool format *is* Anthropic's format
        if self.effort:
            params["output_config"] = {"effort": self.effort}

        if self.use_fallbacks:
            resp = self.client.beta.messages.create(**params, betas=[ANTHROPIC_FALLBACK_BETA], fallbacks="default")
        else:
            resp = self.client.messages.create(**params)
        return from_anthropic(resp)


# --------------------------------------------------------------------------- OpenAI


def to_openai_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    """Convert neutral tool specs to OpenAI Chat Completions `function` tools."""
    return [
        {
            "type": "function",
            "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]},
        }
        for t in tools
    ]


def to_openai_messages(messages: list[Message], system: str | None = None) -> list[dict[str, Any]]:
    """Convert neutral messages to the OpenAI Chat Completions format."""
    out: list[dict[str, Any]] = [{"role": "system", "content": system}] if system else []
    for m in messages:
        role = m["role"]
        if role == "user":
            out.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.get("content") or None}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                    for tc in m["tool_calls"]
                ]
            out.append(msg)
        elif role == "tool":
            content = m["content"]
            if m.get("is_error") and not content.lower().startswith("error"):
                content = f"Error: {content}"  # OpenAI has no is_error flag, so say it in words
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": content})
        else:
            raise ValueError(f"Unknown role: {role!r}")
    return out


_OPENAI_STOP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "refusal",
}


def from_openai(resp: Any) -> LLMResponse:
    """Convert an OpenAI ChatCompletion object to an LLMResponse."""
    choice = resp.choices[0]
    msg = choice.message
    calls: list[ToolCall] = []
    for tc in msg.tool_calls or []:
        if tc.type != "function":
            continue
        try:
            args, err = json.loads(tc.function.arguments or "{}"), None
        except json.JSONDecodeError as exc:
            args, err = {}, f"Invalid JSON arguments: {exc}"
        calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args, error=err))
    stop = "refusal" if getattr(msg, "refusal", None) else _OPENAI_STOP.get(choice.finish_reason or "", "other")
    usage = Usage(resp.usage.prompt_tokens, resp.usage.completion_tokens) if resp.usage else Usage()
    return LLMResponse(
        text=msg.content or getattr(msg, "refusal", None) or "",
        tool_calls=calls,
        stop_reason=stop,
        usage=usage,
        provider="openai",
        raw=resp,
    )


class OpenAILLM(LLM):
    """OpenAI models via the official `openai` SDK (Chat Completions API)."""

    provider = "openai"

    def __init__(self, model: str | None = None, *, client: Any = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL") or ""
        if not self.model:
            raise ValueError(
                "Set OPENAI_MODEL in your .env to a current model ID from https://platform.openai.com/docs/models"
            )
        if client is None:
            from openai import OpenAI

            client = OpenAI()  # reads OPENAI_API_KEY from the environment
        self.client = client

    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(messages, system),
            "max_completion_tokens": max_tokens,
        }
        if tools:
            params["tools"] = to_openai_tools(tools)
        return from_openai(self.client.chat.completions.create(**params))


# --------------------------------------------------------------------------- factory


def get_llm(provider: str | None = None, *, mock_responses: Any = None) -> LLM:
    """Return the LLM chosen by `provider` or the LLM_PROVIDER environment variable.

    Args:
        provider: "mock", "anthropic" or "openai". Defaults to $LLM_PROVIDER, then "mock".
        mock_responses: the script for MockLLM, used only when the provider is "mock".
            Lets an example show a realistic run even with no API key.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()  # picks up examples/.env if present
    except ImportError:
        pass

    name = (provider or os.getenv("LLM_PROVIDER") or "mock").strip().lower()
    if name == "anthropic":
        return AnthropicLLM()
    if name == "openai":
        return OpenAILLM()
    if name == "mock":
        from .mock import MockLLM

        return MockLLM(mock_responses or [], default="(MockLLM) No scripted response left. Set LLM_PROVIDER to use a real model.")
    raise ValueError(f"Unknown LLM_PROVIDER {name!r}. Use 'mock', 'anthropic' or 'openai'.")
