"""Check that your environment is ready.

Run from the examples folder:   python 00-check-setup/main.py
or from this folder:            python main.py

It prints which provider and model are configured, then sends one short
message. With LLM_PROVIDER=mock (the default) this works offline, for free.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, get_llm, user  # noqa: E402

MOCK_REPLY = "Hello! Your setup works (offline, with MockLLM)."


def check(llm: LLM) -> str:
    """Send one message and return a short report."""
    reply = llm.chat([user("Say hello in one short sentence.")], max_tokens=200)
    return "\n".join(
        [
            f"Python:   {sys.version.split()[0]}",
            f"Provider: {llm.provider}",
            f"Model:    {llm.model}",
            f"Reply:    {reply.text}",
            f"Tokens:   {reply.usage.input_tokens} in, {reply.usage.output_tokens} out",
        ]
    )


def main() -> None:
    if sys.version_info < (3, 11):
        sys.exit("These examples need Python 3.11 or newer.")
    llm = get_llm(mock_responses=[MOCK_REPLY])
    print(check(llm))
    print("\n✅ Ready. Next: read docs/01-foundations or run the tests with `pytest`.")


if __name__ == "__main__":
    main()
