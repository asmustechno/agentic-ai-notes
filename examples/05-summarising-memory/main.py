"""Keep a long conversation inside a token budget: trimming versus summarising.

Two strategies for short-term memory, run on the same eight-turn chat:

  * TrimmingMemory     drops the oldest turns once the history is over budget.
  * SummarisingMemory  asks the model to fold the oldest turns into a running
                       summary, kept in the system prompt, and keeps recent turns word for word.

    python main.py                       # from this folder
    python 05-summarising-memory/main.py # from examples/

Read alongside docs/05-memory/05.2-summarisation-and-context-compaction.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, get_llm, user  # noqa: E402

BASE_SYSTEM = "You are a friendly travel planner. Keep answers to two sentences."


def estimate_tokens(messages: list[Message], system: str = "") -> int:
    """Rough count: about 4 characters per token. Use the provider's token counter for real budgets."""
    return (len(system) + sum(len(str(m.get("content") or "")) for m in messages)) // 4


def safe_cut(messages: list[Message], keep_recent: int) -> int:
    """Index where the kept tail should start: at least `keep_recent` messages, starting on a user turn.

    Cutting only before a user message means a tool call is never separated from its tool result.
    """
    cut = max(0, len(messages) - keep_recent)
    while cut > 0 and messages[cut]["role"] != "user":
        cut -= 1
    return cut


@dataclass
class TrimmingMemory:
    """Sliding window: forget the oldest turns when over budget. Cheap, but facts fall off the end."""

    max_tokens: int = 150
    keep_recent: int = 4
    messages: list[Message] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def system(self) -> str:
        return BASE_SYSTEM

    def fit(self) -> None:
        while estimate_tokens(self.messages, self.system()) > self.max_tokens:
            cut = safe_cut(self.messages, self.keep_recent)
            if cut == 0:
                break  # nothing left we are allowed to drop
            # Drop just the oldest whole turn (up to the next user message).
            nxt = next((i for i in range(1, len(self.messages)) if self.messages[i]["role"] == "user"), cut)
            dropped, self.messages = self.messages[:nxt], self.messages[nxt:]
            self.log.append(f"trimmed {len(dropped)} messages")


SUMMARISER_SYSTEM = "You compress conversations. Keep every fact, decision and open question. Drop small talk."
SUMMARY_REQUEST = (
    "Summarise the conversation below for an assistant who will continue it. "
    "Write short bullet points. Keep names, numbers, dates and the user's preferences.\n\n"
)


@dataclass
class SummarisingMemory:
    """Fold old turns into a running summary that lives in the system prompt."""

    llm: LLM  # the model used for summarising (often a smaller, cheaper one)
    max_tokens: int = 150
    keep_recent: int = 4
    summary: str = ""
    messages: list[Message] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def system(self) -> str:
        if not self.summary:
            return BASE_SYSTEM
        return f"{BASE_SYSTEM}\n\n<conversation_summary>\n{self.summary}\n</conversation_summary>"

    def fit(self) -> None:
        if estimate_tokens(self.messages, self.system()) <= self.max_tokens:
            return
        cut = safe_cut(self.messages, self.keep_recent)
        if cut == 0:
            return
        old, self.messages = self.messages[:cut], self.messages[cut:]
        transcript = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in old if m.get("content"))
        if self.summary:
            transcript = f"Earlier summary:\n{self.summary}\n\nNewer turns:\n{transcript}"
        reply = self.llm.chat([user(SUMMARY_REQUEST + transcript)], system=SUMMARISER_SYSTEM, max_tokens=1000)
        self.summary = reply.text.strip()
        self.log.append(f"summarised {len(old)} messages into {estimate_tokens([], self.summary)} tokens")


@dataclass
class ChatBot:
    llm: LLM
    memory: TrimmingMemory | SummarisingMemory
    trace: list[str] = field(default_factory=list)

    def send(self, text: str) -> str:
        self.memory.add(user(text))
        before = len(self.memory.log)
        self.memory.fit()  # compact *before* the call, so the request fits the budget
        system = self.memory.system()
        sent = estimate_tokens(self.memory.messages, system)
        reply = self.llm.chat(self.memory.messages, system=system)
        self.memory.add(reply.to_message())
        note = "; ".join(self.memory.log[before:])
        self.trace.append(f"turn {len(self.trace) + 1}: sent ~{sent:>3} tokens, "
                          f"{len(self.memory.messages) - 1} msgs" + (f"  <- {note}" if note else ""))
        return reply.text


# --------------------------------------------------------------------------- the demo conversation

CONVERSATION = [
    ("Hi! I'm planning four days in Lisbon in May. My budget is 900 euros and I'm vegetarian.",
     "Lovely plan! May is warm and not too crowded, and 900 euros is comfortable for four days."),
    ("Which neighbourhood should I stay in?",
     "Alfama is charming and central, with steep lanes and fado bars. Baixa is flatter if you prefer easy walking."),
    ("Let's go with Alfama. Hostel or hotel?",
     "A good Alfama guesthouse costs about 70 euros a night, which leaves plenty for food and trips."),
    ("What day trip would you suggest?",
     "Sintra: palaces, gardens and forest walks, an easy train ride away."),
    ("How do I get to Sintra?",
     "Take the train from Rossio station. It takes about 40 minutes and runs every 20 minutes."),
    ("What should I pack?",
     "Comfortable shoes for the hills and a light jacket for the evenings."),
    ("Is the 28 tram worth it?",
     "Yes, go early in the morning to avoid queues. It passes right through Alfama."),
    ("Remind me: what is my budget, and is there anything about food I told you?",
     "Your budget is 900 euros, and you're vegetarian, so I'll keep restaurant tips meat-free."),
]
CANNED = dict(CONVERSATION)


def fake_summary(transcript: str) -> str:
    """A rule-based stand-in for a model-written summary, so the demo is offline and repeatable."""
    facts = [
        ("900 euros", "Budget: 900 euros for four days in Lisbon in May."),
        ("vegetarian", "Diet: vegetarian."),
        ("go with Alfama", "Decided: stay in Alfama (guesthouse about 70 euros a night)."),
        ("Sintra", "Day trip: Sintra, train from Rossio, about 40 minutes."),
        ("should I pack", "Pack comfortable shoes and a light jacket."),
    ]
    kept = [line for line in transcript.splitlines() if line.startswith("- ")]  # bullets from the earlier summary
    new = [f"- {line}" for key, line in facts if key in transcript and f"- {line}" not in kept]
    return "\n".join(kept + new)


def fake_model(messages: list[Message]) -> str:
    """Scripted replies: summaries for summarise requests, canned answers for chat turns."""
    last = messages[-1]["content"]
    if last.startswith(SUMMARY_REQUEST):
        return fake_summary(last)
    return CANNED.get(last, "Happy to help with that.")


def run(memory_kind: str, llm: LLM | None = None) -> ChatBot:
    llm = llm or get_llm(mock_responses=[fake_model] * 40)
    memory = SummarisingMemory(llm) if memory_kind == "summarise" else TrimmingMemory()
    bot = ChatBot(llm, memory)
    for question, _ in CONVERSATION:
        bot.send(question)
    return bot


def main() -> None:
    for kind in ("trim", "summarise"):
        bot = run(kind)
        context = bot.memory.system() + " ".join(str(m["content"]) for m in bot.memory.messages[:-1])
        print(f"=== {type(bot.memory).__name__} (budget ~{bot.memory.max_tokens} tokens) ===")
        print("\n".join(bot.trace))
        print(f"Is '900 euros' still in the context of the last turn? {'yes' if '900 euros' in context else 'NO'}")
        if isinstance(bot.memory, SummarisingMemory):
            print(f"Running summary:\n{bot.memory.summary}")
        print()


if __name__ == "__main__":
    main()
