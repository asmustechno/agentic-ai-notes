"""The notes MCP server, tested through a real MCP client. Offline: no model, no network."""

import asyncio
import sys

from mcp import Client, StdioServerParameters

from common.testing import load_example

server_mod = load_example(__file__, "notes_server")
main = load_example(__file__)


async def _with_client(fn, notes=None):
    async with Client(server_mod.build_server(notes)) as client:
        return await fn(client)


def run(fn, notes=None):
    return asyncio.run(_with_client(fn, notes))


def test_server_advertises_tools_with_schemas_and_annotations() -> None:
    async def check(c):
        return {t.name: t for t in (await c.list_tools()).tools}

    tools = run(check)
    assert set(tools) == {"search_notes", "add_note"}
    add = tools["add_note"].input_schema
    assert add["required"] == ["title", "text"]
    assert add["properties"]["title"]["maxLength"] == 40
    assert tools["search_notes"].annotations.read_only_hint is True


def test_add_then_search() -> None:
    async def check(c):
        await c.call_tool("add_note", {"title": "Dentist", "text": "Friday at 15:00"})
        return await c.call_tool("search_notes", {"query": "friday 15:00"})

    result = run(check, notes={})
    assert result.is_error is False
    assert result.structured_content == {"result": ["dentist: Friday at 15:00"]}


def test_bad_input_is_a_tool_error_not_a_crash() -> None:
    async def check(c):
        empty = await c.call_tool("add_note", {"title": "  ", "text": "x"})
        too_long = await c.call_tool("add_note", {"title": "x" * 41, "text": "x"})
        return empty, too_long

    empty, too_long = run(check)
    assert empty.is_error and "title must not be empty" in empty.content[0].text
    assert too_long.is_error and "at most 40 characters" in too_long.content[0].text


def test_resources_and_template() -> None:
    async def check(c):
        index = await c.read_resource("notes://index")
        one = await c.read_resource("notes://trip")
        return index.contents[0].text, one.contents[0].text

    index, trip = run(check)
    assert index.splitlines() == ["groceries", "trip"]
    assert "Lyon" in trip


def test_prompt_is_filled_with_notes_and_argument() -> None:
    async def check(c):
        return await c.get_prompt("weekly_review", {"focus": "travel"})

    prompt = run(check, notes={"a": "b"})
    text = prompt.messages[0].content.text
    assert prompt.messages[0].role == "user"
    assert "- a: b" in text and text.endswith("Focus on travel.")


def test_tour_runs_in_process() -> None:
    lines = asyncio.run(main.tour(server_mod.build_server()))
    assert lines[0].startswith("Connected to notes 1.0.0")
    assert any("is_error=True" in line for line in lines)


def test_server_works_over_stdio_subprocess() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(main.SERVER_FILE)])

    async def check():
        async with Client(params) as c:
            return [t.name for t in (await c.list_tools()).tools]

    assert sorted(asyncio.run(check())) == ["add_note", "search_notes"]
