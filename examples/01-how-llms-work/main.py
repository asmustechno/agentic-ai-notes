"""Two facts about LLM APIs that every agent depends on.

1. The API is stateless: the model remembers nothing between calls.
   To "remember", you send the whole conversation every time.
2. So the input grows every turn, and you pay for every token you resend.

    python main.py                      # from this folder
    python 01-how-llms-work/main.py     # from examples/

Read alongside docs/01-foundations/01.4-how-llms-work.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, get_llm, user  # noqa: E402
from common.llm import to_anthropic_messages  # noqa: E402

# --------------------------------------------------------------------------- counting tokens


def estimate_tokens(text: str) -> int:
    """Rough rule of thumb for English: about 4 characters per token. Never use it for billing."""
    return max(1, len(text) // 4)


def count_tokens(llm: LLM, messages: list[Message], system: str | None = None) -> tuple[int, str]:
    """Count input tokens exactly when the provider offers an API for it, else estimate.

    Returns (tokens, method).
    """
    if llm.provider == "anthropic":
        params = {"model": llm.model, "messages": to_anthropic_messages(messages)}
        if system:
            params["system"] = system
        return llm.client.messages.count_tokens(**params).input_tokens, "exact (Anthropic count_tokens API)"
    text = (system or "") + "".join(str(m.get("content", "")) for m in messages)
    return estimate_tokens(text), "estimate (~4 characters per token)"


# --------------------------------------------------------------------------- statelessness


def remembers_name(messages: list[Message]) -> str:
    """A scripted 'model' that, like a real one, can only use what is in the messages it is sent."""
    said_name = any("my name is sam" in str(m.get("content", "")).lower() for m in messages)
    return "Your name is Sam." if said_name else "I'm sorry, I don't know your name. You haven't told me."


def ask_without_history(llm: LLM) -> str:
    """Two separate calls. The second call does not include the first."""
    llm.chat([user("Hi! My name is Sam.")])
    return llm.chat([user("What's my name?")]).text


def ask_with_history(llm: LLM) -> str:
    """The same two questions, but we resend the conversation each time."""
    history: list[Message] = [user("Hi! My name is Sam.")]
    history.append(llm.chat(history).to_message())
    history.append(user("What's my name?"))
    return llm.chat(history).text


def growing_conversation(llm: LLM, questions: list[str]) -> list[tuple[int, int]]:
    """Ask several questions in one conversation. Returns (turn, input tokens) for each call."""
    history: list[Message] = []
    sizes: list[tuple[int, int]] = []
    for turn, q in enumerate(questions, start=1):
        history.append(user(q))
        reply = llm.chat(history, max_tokens=300)
        sizes.append((turn, reply.usage.input_tokens))
        history.append(reply.to_message())
    return sizes


QUESTIONS = [
    "In one sentence, what is a token?",
    "And what is a context window?",
    "Why does that matter for an agent that runs for 50 steps?",
]
SCRIPTED_ANSWERS = [
    "A token is a small chunk of text, often a word or part of a word, that a model reads and writes.",
    "The context window is the maximum number of tokens the model can take in at once, "
    "including the whole conversation you send it.",
    "Because every step adds tool calls and results to the conversation, a long-running agent "
    "can fill its context window and get slower and more expensive with every step.",
]


def main() -> None:
    print("1) The API is stateless")
    print("   Without history:", ask_without_history(get_llm(mock_responses=[remembers_name] * 2)))
    print("   With history:   ", ask_with_history(get_llm(mock_responses=[remembers_name] * 2)))

    print("\n2) The input grows every turn, because we resend everything")
    for turn, tokens in growing_conversation(get_llm(mock_responses=SCRIPTED_ANSWERS), QUESTIONS):
        print(f"   turn {turn}: {tokens:>4} input tokens  " + "█" * max(1, tokens // 5))

    print("\n3) Counting tokens before you send")
    llm = get_llm(mock_responses=[])
    tokens, method = count_tokens(llm, [user(q) for q in QUESTIONS])
    print(f"   {tokens} tokens, {method}")


if __name__ == "__main__":
    main()
