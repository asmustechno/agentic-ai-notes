"""Vector memory with a toy embedder. Offline, with MockLLM; no embedding API is called."""

from pathlib import Path

from common import MockLLM
from common.testing import load_example

main = load_example(__file__)


def test_embeddings_are_unit_length_and_deterministic() -> None:
    e = main.HashingEmbedder()
    a, b = e.embed("Window seats please"), e.embed("Window seats please")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9


def test_cosine_basics() -> None:
    assert main.cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert main.cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert main.cosine([0.0, 0.0], [1.0, 0.0]) == 0.0  # empty vector never matches


def test_search_ranks_by_similarity_and_drops_weak_matches() -> None:
    mem = main.VectorMemory()
    mem.add("The user prefers window seats on flights.")
    mem.add("The user's daughter Mia is allergic to peanuts.")
    hits = mem.search("window seat on the flight")
    assert [m.text for _, m in hits] == ["The user prefers window seats on flights."]
    assert mem.search("quantum chromodynamics") == []


def test_bag_of_words_misses_synonyms() -> None:
    mem = main.VectorMemory()
    mem.add("The user's daughter Mia is allergic to peanuts.")
    assert mem.search("family food restrictions") == []  # why real systems use an embedding model


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    mem = main.VectorMemory()
    mem.add("Likes jazz", source="chat")
    path = tmp_path / "mem.json"
    mem.save(path)
    loaded = main.VectorMemory.load(path)
    assert loaded.items[0].text == "Likes jazz" and loaded.items[0].meta == {"source": "chat"}
    assert loaded.search("jazz")[0][1].id == 1


def test_session_two_recalls_what_session_one_saved(tmp_path: Path) -> None:
    llm1 = MockLLM(main.SCRIPT_1)
    agent = main.MemoryAgent(llm1, main.VectorMemory())
    agent.run(main.SESSION_1)
    assert {t["name"] for t in llm1.calls[0]["tools"]} == {"remember", "recall"}
    agent.memory.save(tmp_path / "m.json")

    llm2 = MockLLM(main.SCRIPT_2)
    agent2 = main.MemoryAgent(llm2, main.VectorMemory.load(tmp_path / "m.json"))
    answer = agent2.run(main.SESSION_2)
    # The new conversation started empty: memory reached the model only through recall results.
    assert len(llm2.calls[0]["messages"]) == 1
    tool_outputs = [m["content"] for m in llm2.calls[1]["messages"] if m["role"] == "tool"]
    assert "window seats" in tool_outputs[0] and "peanuts" in tool_outputs[1]
    assert answer == "I'll look for flights to Oslo with a window seat, and pack a peanut-free snack for Mia."


def test_main_runs(tmp_path: Path, capsys) -> None:
    main.main(tmp_path / "demo.json")
    out = capsys.readouterr().out
    assert "peanut-free snack" in out and "#1=0.0, #2=0.0, #3=0.0" in out
