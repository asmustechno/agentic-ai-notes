"""The from-scratch agent, and its raw-SDK twins, work end to end. Offline: MockLLM and fake clients."""

from __future__ import annotations

import io
import json
import tokenize
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)
raw_anthropic = load_example(__file__, "raw_anthropic")
raw_openai = load_example(__file__, "raw_openai")


# --------------------------------------------------------------------------- wrapper version


def test_agent_lists_reads_then_answers() -> None:
    llm = MockLLM(main.SCRIPT)
    trace: list[str] = []
    answer = main.run_agent(llm, main.GOAL, main.SYSTEM, trace=trace)
    assert "8080" in answer
    assert len(llm.calls) == 3
    assert trace[0].startswith("list_files({})")
    assert trace[1].startswith("read_file({'path': 'config/app.toml'})")
    assert llm.calls[0]["system"] == main.SYSTEM
    assert [t["name"] for t in llm.calls[0]["tools"]] == ["list_files", "read_file"]


def test_tool_errors_are_sent_back_not_raised() -> None:
    llm = MockLLM([MockLLM.tool_call("read_file", {"path": "nope.txt"}), "That file does not exist."])
    assert main.run_agent(llm, "read nope.txt") == "That file does not exist."
    result = llm.calls[1]["messages"][-1]
    assert result["is_error"] is True and "KeyError" in result["content"]


def test_unknown_tool_is_an_error_result() -> None:
    llm = MockLLM([MockLLM.tool_call("delete_everything"), "ok"])
    main.run_agent(llm, "x")
    assert llm.calls[1]["messages"][-1]["content"] == "Unknown tool 'delete_everything'"


def test_step_limit() -> None:
    llm = MockLLM([MockLLM.tool_call("list_files")] * 5)
    assert main.run_agent(llm, "x", max_steps=2).startswith("Stopped")
    assert len(llm.calls) == 2


def count_code_lines(path: Path) -> int:
    """Lines that hold code: not blank, not only a comment, not part of a docstring."""
    lines: set[int] = set()
    prev = tokenize.NEWLINE
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            prev = tok.type
            continue  # a docstring
        if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT,
                            tokenize.ENDMARKER):
            lines.update(range(tok.start[0], tok.end[0] + 1))
        prev = tok.type
    return len(lines)


def test_the_agent_really_is_about_50_lines() -> None:
    n = count_code_lines(Path(main.__file__))
    print(f"main.py has {n} lines of code")
    assert 45 <= n <= 60


# --------------------------------------------------------------------------- raw Anthropic SDK version


def _anthropic_reply(stop_reason: str, *blocks: Any) -> Any:
    return NS(stop_reason=stop_reason, content=list(blocks))


class FakeAnthropic:
    """Just enough of anthropic.Anthropic for the loop: client.messages.create(...)."""

    def __init__(self, replies: list[Any]) -> None:
        self.replies, self.requests = list(replies), []
        self.messages = NS(create=self._create)

    def _create(self, **params: Any) -> Any:
        self.requests.append(json.loads(json.dumps(params, default=lambda o: o.__dict__)))
        return self.replies.pop(0)


def test_raw_anthropic_loop() -> None:
    client = FakeAnthropic([
        _anthropic_reply("tool_use", NS(type="tool_use", id="toolu_1", name="read_file",
                                        input={"path": "config/app.toml"})),
        _anthropic_reply("end_turn", NS(type="text", text="Port 8080.")),
    ])
    assert raw_anthropic.run_agent("Which port?", client=client) == "Port 8080."
    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[2]["content"] == [
        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "[server]\nport = 8080\nworkers = 4",
         "is_error": False}
    ]
    assert client.requests[0]["model"] == "claude-opus-5-5"


# --------------------------------------------------------------------------- raw OpenAI SDK version


class FakeOpenAI:
    """Just enough of openai.OpenAI for the loop: client.chat.completions.create(...)."""

    def __init__(self, messages: list[Any]) -> None:
        self.replies, self.requests = list(messages), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **params: Any) -> Any:
        self.requests.append(params)
        return NS(choices=[NS(message=self.replies.pop(0))])


def test_raw_openai_loop_and_bad_json() -> None:
    call = NS(id="call_1", type="function", function=NS(name="read_file", arguments='{"path": "config/app.toml"}'))
    bad = NS(id="call_2", type="function", function=NS(name="read_file", arguments='{"path": '))
    client = FakeOpenAI([
        NS(content=None, tool_calls=[call, bad]),
        NS(content="Port 8080.", tool_calls=None),
    ])
    assert raw_openai.run_agent("Which port?", client=client, model="test-model") == "Port 8080."
    history = client.requests[1]["messages"]
    assert history[0]["role"] == "system"
    assert history[3] == {"role": "tool", "tool_call_id": "call_1", "content": "[server]\nport = 8080\nworkers = 4"}
    assert history[4]["content"].startswith("Error: arguments were not valid JSON")
    assert client.requests[0]["tools"][0]["type"] == "function"
