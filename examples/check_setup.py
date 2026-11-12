"""Check that your environment is ready: `python check_setup.py`.

It prints which provider and model are configured, then sends one short
message. With LLM_PROVIDER=mock (the default) this works offline.
"""

from common import get_llm, user


def main() -> None:
    llm = get_llm(mock_responses=["Hello! Your setup works (offline, with MockLLM)."])
    print(f"Provider: {llm.provider}")
    print(f"Model:    {llm.model}")
    reply = llm.chat([user("Say hello in one short sentence.")], max_tokens=200)
    print(f"Reply:    {reply.text}")
    print(f"Tokens:   {reply.usage.input_tokens} in, {reply.usage.output_tokens} out")


if __name__ == "__main__":
    main()
