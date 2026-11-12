"""The well-designed tool validates input, explains errors, and keeps output small. Offline."""

from __future__ import annotations

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)
TOOL = main.SEARCH_ORDERS


def test_schema_is_generated_from_the_pydantic_model() -> None:
    schema = TOOL.spec["input_schema"]
    assert schema["required"] == ["customer_email"]
    assert schema["additionalProperties"] is False  # from extra="forbid"
    assert schema["properties"]["page_size"]["maximum"] == 20
    assert "title" not in schema and "title" not in schema["properties"]["page"]
    assert all("description" in p for p in schema["properties"].values())


def test_description_says_when_to_call_it() -> None:
    assert "Call this whenever" in TOOL.spec["description"]


def test_concise_output_is_much_smaller_than_the_raw_dump() -> None:
    good, is_error = TOOL({"customer_email": "sam@example.com"})
    assert not is_error
    assert len(good) * 5 < len(main.get_data("sam@example.com"))
    assert "uuid" not in good  # low-signal internal IDs left out by default


def test_detailed_format_includes_ids() -> None:
    detailed, _ = TOOL({"customer_email": "sam@example.com", "response_format": "detailed"})
    assert "uuid 6f1c9a2e" in detailed and "carrier FastShip" in detailed


def test_pagination_tells_the_model_what_to_do_next() -> None:
    first, _ = TOOL({"customer_email": "sam@example.com"})
    assert first.endswith("Showing 1-5 of 12 orders. Call again with page=2 for more.")
    last, _ = TOOL({"customer_email": "sam@example.com", "page": 3})
    assert last.endswith("Showing 11-12 of 12 orders.")
    empty, is_error = TOOL({"customer_email": "sam@example.com", "page": 9})
    assert "only 12 orders" in empty and not is_error


def test_validation_errors_are_specific_and_actionable() -> None:
    content, is_error = TOOL({"customer_email": "sam@example.com", "status": "shiped", "page_size": 50})
    assert is_error
    assert "status: Input should be 'pending', 'shipped', 'delivered' or 'cancelled' (you sent 'shiped')" in content
    assert "page_size: Input should be less than or equal to 20 (you sent 50)" in content
    assert "Example of a valid call" in content


def test_missing_and_unknown_arguments() -> None:
    content, is_error = TOOL({"email": "sam@example.com"})
    assert is_error
    assert "- customer_email: Field required" in content
    assert "- email: Extra inputs are not permitted" in content


def test_no_results_suggests_a_fix() -> None:
    content, is_error = TOOL({"customer_email": "nobody@example.com", "status": "pending"})
    assert content.startswith("No orders found for nobody@example.com with status 'pending'")
    assert "omit status" in content and not is_error


def test_agent_recovers_from_a_bad_call() -> None:
    llm = MockLLM(main.SCRIPT)
    log: list[str] = []
    answer = main.run_agent(llm, main.GOAL, [TOOL], log=log)
    assert "#1041" in answer and len(llm.calls) == 3
    first_result = llm.calls[1]["messages"][-1]
    assert first_result["is_error"] is True and "you sent 'shiped'" in first_result["content"]
    assert "#1041 Blue kettle: shipped" in llm.calls[2]["messages"][-1]["content"]


def test_unknown_tool() -> None:
    llm = MockLLM([MockLLM.tool_call("get_data", {"q": "x"}), "ok"])
    main.run_agent(llm, "x", [TOOL])
    assert llm.calls[1]["messages"][-1]["content"] == "Unknown tool 'get_data'. Available: search_orders."
