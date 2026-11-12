"""Tool calls are logged as JSON lines with a run ID, sizes in prod mode, and secrets redacted. Offline."""

import io
import json
import logging
import threading

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def run(mode: str, script=None):
    buffer = io.StringIO()
    agent = main.LoggingAgent(llm=MockLLM(script or main.SCRIPT), logger=main.make_logger(buffer), mode=mode)
    answer = agent.run(main.GOAL, run_id="run-test")
    lines = [json.loads(line) for line in buffer.getvalue().splitlines()]
    return answer, lines, buffer.getvalue()


def test_every_line_is_json_with_the_run_id() -> None:
    _, lines, _ = run("prod")
    assert [e["event"] for e in lines] == [
        "run.start", "model.call", "tool.call", "model.call", "tool.call", "model.call", "run.end",
    ]
    assert {e["run_id"] for e in lines} == {"run-test"}


def test_prod_mode_logs_sizes_not_payloads() -> None:
    _, lines, raw = run("prod")
    tool_line = next(e for e in lines if e["event"] == "tool.call")
    assert tool_line["arg_names"] == ["email"]
    assert tool_line["result_chars"] > 0 and "duration_ms" in tool_line
    assert "arguments" not in tool_line and "result_preview" not in tool_line
    assert "ana@example.com" not in raw and "4242" not in raw


def test_debug_mode_logs_values_but_redacted() -> None:
    _, lines, raw = run("debug")
    tool_line = next(e for e in lines if e["event"] == "tool.call")
    assert tool_line["arguments"] == {"email": "[EMAIL]"}
    assert "[CARD]" in tool_line["result_preview"]
    assert "ana@example.com" not in raw and "4242" not in raw


def test_redact_handles_keys_patterns_and_nesting() -> None:
    data = {
        "headers": {"Authorization": "Bearer abcdefgh12345"},
        "api_key": "anything",
        "note": "key sk-ant-api03-abcdefghijk and card 4111-1111-1111-1111, mail bob@corp.io",
        "items": [{"password": "hunter2"}, "sk-proj-12345678abcd"],
        "count": 3,
    }
    out = main.redact(data)
    assert out["headers"]["Authorization"] == "[REDACTED]"
    assert out["api_key"] == "[REDACTED]"
    assert out["note"] == "key [REDACTED_KEY] and card [CARD], mail [EMAIL]"
    assert out["items"] == [{"password": "[REDACTED]"}, "[REDACTED_KEY]"]
    assert out["count"] == 3
    assert data["api_key"] == "anything"  # the original is not modified


def test_failed_tool_is_logged_as_warning_and_sent_back_as_error() -> None:
    script = [MockLLM.tool_call("find_customer", {"email": "nobody@example.com"}), "I couldn't find that account."]
    buffer = io.StringIO()
    llm = MockLLM(script)
    main.LoggingAgent(llm=llm, logger=main.make_logger(buffer)).run(main.GOAL, run_id="r1")
    tool_line = next(json.loads(x) for x in buffer.getvalue().splitlines() if '"tool.call"' in x)
    assert tool_line["level"] == "warning" and tool_line["ok"] is False
    assert tool_line["error_type"] == "KeyError"
    sent = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"][0]
    assert sent["is_error"] is True


def test_run_ids_do_not_leak_between_threads() -> None:
    buffer = io.StringIO()
    logger = main.make_logger(buffer)

    def work(rid: str) -> None:
        with main.run_context(rid):
            for _ in range(20):
                logger.info("tick", extra={"me": rid})

    threads = [threading.Thread(target=work, args=(f"run-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = [json.loads(x) for x in buffer.getvalue().splitlines()]
    assert len(lines) == 80 and all(e["run_id"] == e["me"] for e in lines)
    assert main.RUN_ID.get() is None


def test_logger_has_no_duplicate_handlers() -> None:
    buffer = io.StringIO()
    main.make_logger(buffer)
    logger = main.make_logger(buffer)
    assert len(logger.handlers) == 1 and isinstance(logger.handlers[0], logging.StreamHandler)
