"""Designing a tool the model can use well: a bad version and a good version, side by side.

The good tool has a clear name and description, validated inputs (pydantic),
error messages that say how to fix the call, concise high-signal output, and
pagination instead of dumping everything.

    python main.py                   # from this folder
    python 03-tool-design/main.py    # from examples/

Read alongside docs/03-tools-and-function-calling/03.4-designing-good-tools.md.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `common` importable

from common import LLM, Message, MockLLM, ToolCall, ToolSpec, get_llm, tool_result, user  # noqa: E402

# --------------------------------------------------------------------------- fake data

ORDERS = [
    {"uuid": "6f1c9a2e-8d4b-4e7a-9b1f-3c2d5e6f7a8b", "order_no": 1041, "email": "sam@example.com",
     "item": "Blue kettle", "status": "shipped", "carrier": "FastShip", "eta": "2026-11-15",
     "sku": "KTL-BLU-17", "warehouse_id": 7, "created_ts": 1762905600},
    {"uuid": "0b2e4c6a-1f3d-4a5b-8c7d-9e0f1a2b3c4d", "order_no": 1022, "email": "sam@example.com",
     "item": "Tea towels (3)", "status": "delivered", "carrier": "FastShip", "eta": "2026-10-30",
     "sku": "TWL-SET-03", "warehouse_id": 2, "created_ts": 1761696000},
] + [
    {"uuid": f"00000000-0000-4000-8000-{n:012d}", "order_no": 1000 + n, "email": "sam@example.com",
     "item": f"Mug #{n}", "status": "delivered", "carrier": "PostCo", "eta": "2026-09-01",
     "sku": f"MUG-{n:03d}", "warehouse_id": 1, "created_ts": 1756684800 + n}
    for n in range(1, 11)
]

# --------------------------------------------------------------------------- the BAD tool


def get_data(q: str) -> str:
    """Everything about everything, as raw JSON."""
    return json.dumps([o for o in ORDERS if q in json.dumps(o)])


BAD_SPEC: ToolSpec = {
    "name": "get_data",
    "description": "Gets data.",  # gets WHAT data? when should the model call it?
    "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},  # q = ??? no description
}

# --------------------------------------------------------------------------- the GOOD tool


# pydantic validates the inputs AND generates the JSON Schema the model reads.
# (No class docstring: pydantic would copy it into the schema, where it only costs tokens.)
class SearchOrdersInput(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown arguments are an error -> "additionalProperties": false

    customer_email: str = Field(description="The customer's email address, e.g. 'sam@example.com'.")
    status: Literal["pending", "shipped", "delivered", "cancelled"] | None = Field(
        default=None, description="Only return orders with this status. Omit to return every status."
    )
    page: int = Field(default=1, ge=1, description="Page number, starting at 1.")
    page_size: int = Field(default=5, ge=1, le=20, description="Orders per page, 1 to 20. Default 5.")
    response_format: Literal["concise", "detailed"] = Field(
        default="concise",
        description="'concise' returns one line per order. 'detailed' adds carrier, SKU and internal IDs.",
    )


def search_orders(args: SearchOrdersInput) -> str:
    """Find a customer's orders, newest first, one page at a time."""
    found = [o for o in ORDERS if o["email"] == args.customer_email.strip().lower()
             and (args.status is None or o["status"] == args.status)]
    if not found:
        return (f"No orders found for {args.customer_email}"
                + (f" with status '{args.status}'" if args.status else "")
                + ". Check the email address, or omit status to search every status.")
    found.sort(key=lambda o: o["created_ts"], reverse=True)
    start = (args.page - 1) * args.page_size
    page = found[start:start + args.page_size]
    if not page:
        return f"Page {args.page} is empty: there are only {len(found)} orders. Use a smaller page number."
    if args.response_format == "concise":
        lines = [f"#{o['order_no']} {o['item']}: {o['status']}, ETA {o['eta']}" for o in page]
    else:
        lines = [f"#{o['order_no']} {o['item']}: {o['status']}, ETA {o['eta']}, carrier {o['carrier']}, "
                 f"sku {o['sku']}, uuid {o['uuid']}" for o in page]
    shown = f"Showing {start + 1}-{start + len(page)} of {len(found)} order{'s' if len(found) != 1 else ''}."
    more = f" Call again with page={args.page + 1} for more." if start + len(page) < len(found) else ""
    return "\n".join(lines) + f"\n{shown}{more}"


@dataclass
class Tool:
    """A function plus the description the model reads, with validation built in."""

    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[Any], str]

    @property
    def spec(self) -> ToolSpec:
        return {"name": self.name, "description": self.description, "input_schema": clean_schema(self.input_model)}

    def __call__(self, arguments: dict[str, Any]) -> tuple[str, bool]:
        """Validate, then run. Returns (content, is_error). Errors explain how to fix the call."""
        try:
            args = self.input_model.model_validate(arguments)
        except ValidationError as exc:
            return friendly_errors(self.name, exc), True
        try:
            return self.fn(args), False
        except Exception as exc:
            return f"{self.name} failed unexpectedly ({type(exc).__name__}). Try again or ask the user for help.", True


def clean_schema(model: type[BaseModel]) -> dict[str, Any]:
    """pydantic's JSON Schema without the 'title' keys, which only add tokens for the model."""

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if not (k == "title" and isinstance(v, str))}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    return strip(model.model_json_schema())


def friendly_errors(tool_name: str, exc: ValidationError) -> str:
    """Turn pydantic's errors into one short, actionable message for the model."""
    problems = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "arguments"
        sent = f" (you sent {err['input']!r})" if err["type"] != "missing" else ""
        problems.append(f"- {field}: {err['msg']}{sent}")
    example = '{"customer_email": "sam@example.com", "status": "shipped"}'
    return f"Invalid arguments for {tool_name}:\n" + "\n".join(problems) + f"\nExample of a valid call: {example}"


SEARCH_ORDERS = Tool(
    name="search_orders",
    description=(
        "Search one customer's orders by email address, newest first. Call this whenever the user asks "
        "about an order's status, delivery date or history. Returns one line per order and says when "
        "there are more pages. Do not guess order details: call this tool."
    ),
    input_model=SearchOrdersInput,
    fn=search_orders,
)

# --------------------------------------------------------------------------- a tiny agent loop using the tool


def run_agent(llm: LLM, goal: str, tools: list[Tool], max_steps: int = 6, log: list[str] | None = None) -> str:
    registry = {t.name: t for t in tools}
    messages: list[Message] = [user(goal)]
    for _ in range(max_steps):
        reply = llm.chat(messages, tools=[t.spec for t in tools])
        messages.append(reply.to_message())
        if not reply.tool_calls:
            return reply.text
        for call in reply.tool_calls:
            content, is_error = run_call(call, registry)
            if log is not None:
                log.append(f"{call.name}({call.arguments})\n{'ERROR ' if is_error else ''}{content}")
            messages.append(tool_result(call.id, content, is_error=is_error))
    return "Stopped: step limit reached."


def run_call(call: ToolCall, registry: dict[str, Tool]) -> tuple[str, bool]:
    if call.name not in registry:
        return f"Unknown tool '{call.name}'. Available: {', '.join(registry)}.", True
    return registry[call.name](call.arguments)


GOAL = "Has the blue kettle that sam@example.com ordered shipped yet? When will it arrive?"
SCRIPT = [
    MockLLM.tool_call("search_orders", {"customer_email": "sam@example.com", "status": "shiped", "page_size": 50}),
    MockLLM.tool_call("search_orders", {"customer_email": "sam@example.com", "status": "shipped"}),
    "Yes. Sam's blue kettle (order #1041) has shipped and is due on 15 November 2026.",
]


def pretty(obj: Any, indent: int = 0, width: int = 100) -> str:
    """JSON, indented, but with any part that fits on one line kept on one line."""
    flat = json.dumps(obj, ensure_ascii=False)
    if len(flat) + indent <= width or not isinstance(obj, (dict, list)) or not obj:
        return flat
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k)}: {pretty(v, indent + 2, width)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    items = [f"{inner}{pretty(v, indent + 2, width)}" for v in obj]
    return "[\n" + ",\n".join(items) + f"\n{pad}]"


def main() -> None:
    print("1) What the model sees for each tool\n")
    print(f"BAD : {json.dumps(BAD_SPEC)}\n")
    print(f"GOOD: {pretty(SEARCH_ORDERS.spec)}\n")

    print("2) Same question, output size\n")
    bad = get_data("sam@example.com")
    good, _ = SEARCH_ORDERS({"customer_email": "sam@example.com"})
    print(f"BAD  get_data returns {len(bad):>5} characters (about {len(bad) // 4} tokens): every field of all 12 orders")
    print(f"GOOD search_orders returns {len(good):>3} characters (about {len(good) // 4} tokens):\n{good}\n")

    print("3) An agent run: a bad call, a helpful error, a fixed call\n")
    log: list[str] = []
    answer = run_agent(get_llm(mock_responses=SCRIPT), GOAL, [SEARCH_ORDERS], log=log)
    for i, entry in enumerate(log, 1):
        print(f"call {i}: {entry}\n")
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
