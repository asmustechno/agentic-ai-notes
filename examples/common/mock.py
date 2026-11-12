"""MockLLM: a fake model that returns scripted replies.

It lets every example and test run offline, for free, and with the same result
every time. It also records every request, so tests can check exactly what an
agent sent to the model.

    from common import MockLLM, user

    llm = MockLLM([
        MockLLM.tool_call("get_weather", {"city": "Paris"}),
        "It is 18°C and sunny in Paris.",
    ])
    first = llm.chat([user("Weather in Paris?")])   # -> asks for get_weather
    ...
    assert llm.calls[0]["messages"][0]["content"] == "Weather in Paris?"

A script entry can be:
  * a string                 -> a plain text reply
  * an LLMResponse           -> returned as-is (use MockLLM.text / MockLLM.tool_call)
  * a function(messages)     -> called with the conversation; returns a string or LLMResponse,
                                for replies that depend on what the agent sent
"""

from __future__ import annotations

import copy
import itertools
from collections import deque
from collections.abc import Callable, Iterable
from typing import Any, Union

from .llm import DEFAULT_MAX_TOKENS, LLM, LLMResponse, Message, ToolCall, ToolSpec, Usage

ScriptItem = Union[str, LLMResponse, Callable[[list[Message]], Union[str, LLMResponse]]]


class MockLLMExhausted(RuntimeError):
    """Raised when the agent asks for more replies than the script contains."""


class MockLLM(LLM):
    """A scripted, offline stand-in for a real model."""

    provider = "mock"
    model = "mock-model"
    _ids = itertools.count(1)

    def __init__(self, responses: Iterable[ScriptItem] = (), *, default: str | None = None) -> None:
        """
        Args:
            responses: the replies to return, in order.
            default: text to return once the script runs out. If None (the default),
                running out raises MockLLMExhausted, which is what you want in tests.
        """
        self.script: deque[ScriptItem] = deque(responses)
        self.default = default
        self.calls: list[dict[str, Any]] = []

    # ---- helpers for writing scripts

    @staticmethod
    def text(text: str) -> LLMResponse:
        """A plain text reply that ends the turn."""
        return LLMResponse(text=text, stop_reason="end_turn")

    @classmethod
    def tool_call(cls, name: str, arguments: dict[str, Any] | None = None, *, text: str = "") -> LLMResponse:
        """A reply that asks for one tool to be run."""
        return cls.tool_calls([(name, arguments or {})], text=text)

    @classmethod
    def tool_calls(cls, calls: Iterable[tuple[str, dict[str, Any]]], *, text: str = "") -> LLMResponse:
        """A reply that asks for several tools to be run in parallel."""
        return LLMResponse(
            text=text,
            tool_calls=[ToolCall(id=f"call_{next(cls._ids)}", name=n, arguments=a) for n, a in calls],
            stop_reason="tool_use",
        )

    # ---- the LLM interface

    def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        self.calls.append(
            {"messages": copy.deepcopy(messages), "system": system, "tools": tools, "max_tokens": max_tokens}
        )
        if self.script:
            item = self.script.popleft()
        elif self.default is not None:
            item = self.default
        else:
            raise MockLLMExhausted(
                f"MockLLM script ran out after {len(self.calls) - 1} replies. "
                "The agent made more model calls than the test expected."
            )

        if callable(item) and not isinstance(item, LLMResponse):
            item = item(messages)
        resp = self.text(item) if isinstance(item, str) else copy.copy(item)
        resp.provider = "mock"
        resp.usage = _estimate_usage(messages, system, resp)
        return resp

    @property
    def remaining(self) -> int:
        """How many scripted replies are left."""
        return len(self.script)


def _estimate_usage(messages: list[Message], system: str | None, resp: LLMResponse) -> Usage:
    """Rough token counts (about 4 characters per token), so cost examples have numbers to show.

    Real providers count tokens with their own tokenizers; never use this for billing.
    """
    sent = len(system or "") + sum(len(str(m.get("content", ""))) for m in messages)
    received = len(resp.text) + sum(len(str(tc.arguments)) for tc in resp.tool_calls)
    return Usage(input_tokens=max(1, sent // 4), output_tokens=max(1, received // 4))
