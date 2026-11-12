"""One task, solved three ways: chatbot, workflow and agent.

Task: a customer asks "Where is my order 1234? Will it arrive before Friday?"

    python main.py            # from this folder
    python 01-chatbot-workflow-agent/main.py   # from examples/

Read alongside docs/01-foundations/01.2-chatbot-vs-workflow-vs-agent.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, MockLLM, get_llm, tool_result, user  # noqa: E402

QUESTION = "Where is my order 1234? Will it arrive before Friday?"

# --------------------------------------------------------------------------- a fake shop backend

ORDERS = {"1234": {"item": "Desk lamp", "status": "shipped", "carrier": "FastShip", "tracking_id": "FS-998"}}
TRACKING = {"FS-998": {"location": "Regional depot", "estimated_delivery": "Thursday"}}


def get_order(order_id: str) -> str:
    """Look up an order. Returns JSON, or an error message the model can read."""
    order = ORDERS.get(order_id)
    return json.dumps(order) if order else f"No order found with id {order_id!r}."


def get_tracking(tracking_id: str) -> str:
    """Look up a parcel's tracking status."""
    status = TRACKING.get(tracking_id)
    return json.dumps(status) if status else f"No tracking found for {tracking_id!r}."


TOOLS = {"get_order": get_order, "get_tracking": get_tracking}
TOOL_SPECS = [
    {
        "name": "get_order",
        "description": "Look up a customer's order by its order id. Returns the item, status, carrier and tracking id.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order number, e.g. '1234'."}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_tracking",
        "description": "Look up where a parcel is and when it should be delivered, using the tracking id from get_order.",
        "input_schema": {
            "type": "object",
            "properties": {"tracking_id": {"type": "string", "description": "The tracking id, e.g. 'FS-998'."}},
            "required": ["tracking_id"],
        },
    },
]

# --------------------------------------------------------------------------- 1. chatbot


def chatbot(llm: LLM, question: str) -> str:
    """One model call. No data, no tools: the model can only use what it already knows."""
    return llm.chat([user(question)], system="You are a helpful shop assistant.").text


# --------------------------------------------------------------------------- 2. workflow


def workflow(llm: LLM, question: str) -> str:
    """Fixed steps written in code. The model only writes the final reply."""
    match = re.search(r"\b(\d{4,})\b", question)  # step 1: code finds the order id
    if not match:
        return "Please include your order number."  # the path is fixed, so code must handle every case
    order = json.loads(get_order(match.group(1)))  # step 2: code calls the order system
    tracking = json.loads(get_tracking(order["tracking_id"]))  # step 3: code calls the tracking system
    prompt = f"Customer question: {question}\nOrder: {json.dumps(order)}\nTracking: {json.dumps(tracking)}"
    return llm.chat([user(prompt)], system="Answer the customer using only the data given.").text  # step 4


# --------------------------------------------------------------------------- 3. agent

AGENT_SYSTEM = "You are a shop assistant. Use the tools to look up real order data before answering."


def agent(llm: LLM, question: str, max_steps: int = 5) -> tuple[str, list[str]]:
    """The model decides which tools to call, in what order, and when it is done."""
    messages = [user(question)]
    trace: list[str] = []
    for _ in range(max_steps):
        reply = llm.chat(messages, system=AGENT_SYSTEM, tools=TOOL_SPECS)
        messages.append(reply.to_message())
        if not reply.tool_calls:  # no tool requested: the model is done
            return reply.text, trace
        for call in reply.tool_calls:  # run each tool the model asked for
            result = TOOLS[call.name](**call.arguments)
            trace.append(f"{call.name}({call.arguments}) -> {result}")
            messages.append(tool_result(call.id, result))
    return "Sorry, I could not finish in time.", trace


# --------------------------------------------------------------------------- offline scripts

CHATBOT_SCRIPT = [
    "I'm sorry, I can't look up orders. Please check your confirmation email for tracking details.",
]
WORKFLOW_SCRIPT = [
    "Good news! Your desk lamp (order 1234) has shipped with FastShip and is due on Thursday, "
    "so it should arrive before Friday.",
]
AGENT_SCRIPT = [
    MockLLM.tool_call("get_order", {"order_id": "1234"}),
    MockLLM.tool_call("get_tracking", {"tracking_id": "FS-998"}),
    "Your desk lamp (order 1234) is at the FastShip regional depot and is due on Thursday, "
    "so it should arrive before Friday.",
]


def main() -> None:
    print(f"Customer: {QUESTION}\n")

    print("1) CHATBOT  (one call, no tools)")
    print(f"   {chatbot(get_llm(mock_responses=CHATBOT_SCRIPT), QUESTION)}\n")

    print("2) WORKFLOW (code decides the steps)")
    print(f"   {workflow(get_llm(mock_responses=WORKFLOW_SCRIPT), QUESTION)}\n")

    print("3) AGENT    (the model decides the steps)")
    answer, trace = agent(get_llm(mock_responses=AGENT_SCRIPT), QUESTION)
    for step in trace:
        print(f"   tool: {step}")
    print(f"   {answer}")


if __name__ == "__main__":
    main()
