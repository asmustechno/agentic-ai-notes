"""Handoffs pass control between peers. Offline, with MockLLM."""

from common import MockLLM, user
from common.testing import load_example

main = load_example(__file__)


def llms_with(**scripts: list) -> dict[str, MockLLM]:
    return {name: MockLLM(scripts.get(name, [])) for name in ("triage", "billing", "tech")}


def test_triage_hands_off_and_billing_answers_directly() -> None:
    llms = llms_with(**main.SCRIPTS)
    runner = main.build_runner(llms)
    answer, who = runner.run([user(main.QUESTION)], start="triage")
    assert who == "billing"
    assert "RR-001" in answer
    assert len(llms["triage"].calls) == 1  # triage never gets control back
    assert main.REFUNDS == [{"invoice_id": "INV-882", "reason": "Duplicate charge on 2026-11-01"}]


def test_handoffs_are_offered_as_transfer_tools() -> None:
    llms = llms_with(**main.SCRIPTS)
    main.build_runner(llms).run([user(main.QUESTION)], start="triage")
    assert [t["name"] for t in llms["triage"].calls[0]["tools"]] == ["transfer_to_billing", "transfer_to_tech"]
    billing_tools = [t["name"] for t in llms["billing"].calls[0]["tools"]]
    assert billing_tools == ["list_charges", "open_refund_request", "transfer_to_tech"]


def test_receiver_sees_full_history_with_its_own_instructions_by_default() -> None:
    llms = llms_with(**main.SCRIPTS)
    main.build_runner(llms).run([user(main.QUESTION)], start="triage")
    first = llms["billing"].calls[0]
    assert first["system"] == main.BILLING_PROMPT
    assert first["messages"][0]["content"] == main.QUESTION
    assert first["messages"][-1]["content"] == "Transferred to billing."


def test_history_filter_gives_receiver_a_clean_start() -> None:
    llms = llms_with(**main.SCRIPTS)
    main.build_runner(llms, filter_history=True).run([user(main.QUESTION)], start="triage")
    assert llms["billing"].calls[0]["messages"] == [user(main.QUESTION)]


def test_tech_question_goes_to_tech() -> None:
    llms = llms_with(
        triage=[MockLLM.tool_call("transfer_to_tech", {"reason": "sync is slow"})],
        tech=[MockLLM.tool_call("check_service_status", {"service": "sync"}), "Sync is degraded right now."],
    )
    answer, who = main.build_runner(llms).run([user("Sync is slow today")], start="triage")
    assert who == "tech" and "degraded" in answer


def test_ping_pong_is_capped() -> None:
    llms = llms_with(
        triage=[MockLLM.tool_call("transfer_to_billing", {"reason": "x"})],
        billing=[MockLLM.tool_call("transfer_to_tech", {"reason": "x"})],
        tech=[MockLLM.tool_call("transfer_to_billing", {"reason": "x"}), "Tech answers itself."],
    )
    runner = main.build_runner(llms)
    runner.max_handoffs = 2
    answer, who = runner.run([user("?")], start="triage")
    assert (answer, who) == ("Tech answers itself.", "tech")
    refused = llms["tech"].calls[1]["messages"][-1]
    assert refused["is_error"] and "limit" in refused["content"]
    assert sum("handoff ->" in line for line in runner.trace) == 2
