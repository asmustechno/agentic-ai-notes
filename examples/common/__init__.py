"""Shared helpers for every example: a provider-neutral LLM wrapper and MockLLM."""

from .llm import (
    LLM,
    AnthropicLLM,
    LLMResponse,
    Message,
    OpenAILLM,
    ToolCall,
    ToolSpec,
    Usage,
    get_llm,
    tool_result,
    user,
)
from .mock import MockLLM, MockLLMExhausted

__all__ = [
    "LLM",
    "AnthropicLLM",
    "LLMResponse",
    "Message",
    "MockLLM",
    "MockLLMExhausted",
    "OpenAILLM",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "get_llm",
    "tool_result",
    "user",
]
