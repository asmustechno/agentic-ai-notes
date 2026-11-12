# 06 · Agentic RAG

The same question answered by **classic RAG** (always retrieve the top 2 chunks, then answer once) and by an **agent** that has a `search_docs` tool and decides when, what and how often to search. Used in [6.4 Agentic RAG](../../docs/06-rag-for-agents/06.4-agentic-rag.md) and [6.1 RAG in 5 minutes](../../docs/06-rag-for-agents/06.1-rag-in-5-minutes.md).

The search engine is a tiny pure-Python vector index (hashed bag-of-words plus cosine similarity) over eight short documents. Real systems use an embedding model and a vector database.

## Run it

```bash
cd examples
python 06-agentic-rag/main.py
```

Output (offline, with `MockLLM`):

```text
Q: How much does the plan with SSO cost?

1) CLASSIC RAG  retrieved ['sso.md', 'changelog.md'] for the raw question
   SSO is available on the Business plan [sso.md], but the documents provided don't say what the Business plan costs.

2) AGENTIC RAG
   Q: How much does the plan with SSO cost?
      step 1: search_docs('SSO single sign-on plan') -> ['sso.md']
      step 2: search_docs('Business plan price per month') -> ['pricing.md', 'sso.md', 'limits.md']
      step 3: answer
   A: SSO is only on the Business plan [sso.md], which costs $199 per month, excluding VAT [pricing.md].

   Q: Can I install Acme Cloud on my own servers?
      step 1: search_docs('on-premises install') -> nothing
      step 2: search_docs('self-hosted deployment own servers') -> nothing
      step 3: answer
   A: I couldn't find that in the Acme Cloud docs: they say nothing about running it on your own servers.

   Q: Hi! What can you help me with?
      step 1: answer
   A: I can answer questions about Acme Cloud's plans, pricing, backups, data regions, support and API limits.
```

What to notice:

- **Multi-hop.** The price of "the plan with SSO" is in a document that shares no words with the question. Classic RAG retrieves two SSO documents and can only admit it doesn't know. The agent finds the plan name first, then searches for that plan's price.
- **Not found.** The agent rewrites its query once, finds nothing above the score threshold, and says so instead of guessing.
- **No search when none is needed.** A greeting goes straight to an answer.

## Test it

```bash
pytest 06-agentic-rag
```

## Things to try

- Set `k=4` in `classic_rag`. Does `pricing.md` get in? What else comes with it?
- Lower `MIN_SCORE` to `0.0`. What does `search_docs("on-premises install")` return now, and why is that worse for the agent?
- Run with a real model (`LLM_PROVIDER=anthropic` or `openai`) and compare its queries with the scripted ones.
