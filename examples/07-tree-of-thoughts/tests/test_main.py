"""Tree-of-thoughts BFS: proposals are checked, states are scored and pruned, and the cost is many calls."""

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def _tot(breadth: int = 3) -> tuple[main.TreeOfThoughts, MockLLM]:
    llm = MockLLM([main.mock_model] * 500)
    return main.TreeOfThoughts(llm, breadth=breadth), llm


def test_solves_the_paper_example() -> None:
    tot, llm = _tot()
    solution = tot.solve(main.PUZZLE)
    assert solution is not None and solution.numbers == (24,)
    assert len(solution.steps) == 3
    assert len(llm.calls) > 10  # search costs many model calls


def test_bad_arithmetic_from_the_model_is_rejected() -> None:
    start = main.State((4, 9, 10, 13))
    assert main.check(start, "13 - 9 = 4 (left: 4 4 10)") == main.State((4, 4, 10), ("13 - 9 = 4 (left: 4 4 10)",))
    assert main.check(start, "13 - 9 = 5 (left: 4 5 10)") is None  # wrong sum
    assert main.check(start, "13 - 7 = 6 (left: 4 6 9 10)") is None  # 7 is not available
    assert main.check(start, "13 - 9 = 4 (left: 4 10)") is None  # lost a number
    assert main.check(start, "I think we should multiply") is None  # not a thought at all


def test_frontier_never_exceeds_breadth() -> None:
    tot, _ = _tot(breadth=2)
    tot.solve(main.PUZZLE)
    for line in tot.log:
        assert line.count("[") <= 2


def test_prompts_sent_to_the_model() -> None:
    tot, llm = _tot()
    tot.solve(main.PUZZLE)
    first = llm.calls[0]["messages"][0]["content"]
    assert first.startswith("Propose") and first.endswith("Input: 4 9 10 13")
    assert any(c["messages"][0]["content"].startswith("Evaluate") for c in llm.calls)


def test_evaluator_values() -> None:
    assert main.mock_evaluate([4, 6]).endswith("sure")
    assert main.mock_evaluate([1, 1]).endswith("impossible")
    assert main.mock_evaluate([4, 4, 10]).endswith("sure")  # 10 - 4 = 6, 4 * 6 = 24
    assert main.mock_evaluate([1, 1, 1]).endswith("impossible")  # too small


def test_unsolvable_puzzle_returns_none() -> None:
    tot, _ = _tot()
    assert tot.solve([1, 1, 1, 1]) is None
