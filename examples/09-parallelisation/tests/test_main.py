"""Parallelisation: sectioning and voting, run concurrently. Offline, with MockLLM."""

import time

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_sectioning_sends_one_focused_call_per_aspect() -> None:
    llm = MockLLM([main.mock_review] * 3)
    report = main.sectioned_review(llm, main.CODE)
    assert list(report) == ["security", "performance", "readability"]
    assert "SQL injection" in report["security"]
    systems = sorted(c["system"] for c in llm.calls)
    assert len(systems) == 3 and all("ONLY" in s for s in systems)


def test_parallel_is_faster_than_sequential() -> None:
    delay = 0.2
    llm = MockLLM([main.slow(main.mock_review, delay)] * 3)
    start = time.perf_counter()
    main.sectioned_review(llm, main.CODE)
    assert time.perf_counter() - start < 3 * delay  # three calls overlapped


def test_run_parallel_keeps_order_and_captures_failures() -> None:
    def work(x: int) -> int:
        if x == 2:
            raise ValueError("bad item")
        time.sleep(0.05 * (3 - x))  # later items finish first
        return x * 10

    results = main.run_parallel(work, [0, 1, 2, 3])
    assert results[0] == 0 and results[1] == 10 and results[3] == 30
    assert isinstance(results[2], ValueError)


def test_voting_counts_and_threshold() -> None:
    result = main.vote(MockLLM(main.MOCK_VOTES), main.CODE, n=5, threshold=3)
    assert (result.yes, result.no, result.abstain, result.flagged) == (3, 1, 1, True)
    stricter = main.vote(MockLLM(main.MOCK_VOTES), main.CODE, n=5, threshold=4)
    assert not stricter.flagged


def test_votes_use_reworded_prompts() -> None:
    llm = MockLLM(["NO"] * 3)
    main.vote(llm, main.CODE, n=3)
    questions = {c["messages"][0]["content"].split("\n")[0] for c in llm.calls}
    assert questions == set(main.VOTE_PROMPTS)


def test_parse_vote() -> None:
    assert main.parse_vote("YES. It is.") == "YES"
    assert main.parse_vote("no, it's fine") == "NO"
    assert main.parse_vote("Possibly") == "ABSTAIN"
    assert main.parse_vote("") == "ABSTAIN"
