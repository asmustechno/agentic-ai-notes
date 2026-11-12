# 18 · Project 3: RAG agent over your PDFs

Ask questions of your own documents: ingest, chunk, embed, search, and answer with citations that the code checks. The full guide, with the spec, milestones and stretch goals, is [18.3 Project 3: RAG agent over your PDFs](../../docs/18-projects/18.3-project-3-rag-over-your-pdfs.md).

## The spec in brief

| | |
| --- | --- |
| **Goal** | Answer only from the user's files, cite the passage behind every fact, and say so when the answer isn't there. |
| **Pipeline** | load `.txt`/`.md`/`.pdf` → chunk by paragraph (max 80 words, headings kept) → embed → in-memory vector index |
| **Embedder** | A pure-Python hashed bag of words, so it runs offline. Swap in a real embedding model for real use. |
| **Tool** | `search_docs(query, k)` returns passages with ids like `acme-expenses-policy.md#4` |
| **Done when** | `pytest 18-project-3-rag-over-pdfs` passes against your code |

## Layout

```text
18-project-3-rag-over-pdfs/
├── requirements.txt     ← pypdf, only needed for PDF files
├── sample_docs/         ← two small fictional company documents
├── starter/main.py      ← you build here: runnable skeleton with # TODO markers
├── solution/main.py     ← a complete reference solution
└── tests/test_solution.py
```

## Run it

From `examples/`:

```bash
python 18-project-3-rag-over-pdfs/starter/main.py    # tells you what is still missing
python 18-project-3-rag-over-pdfs/solution/main.py   # the finished agent on sample_docs/, offline
```

Output of the solution (offline, with `MockLLM`):

```text
Indexed 13 chunks from 2 files: acme-expenses-policy.md, acme-remote-work-guide.md

Question: What's the hotel limit per night in London, and do I need a receipt for a €20 taxi?
  step 1: search_docs('hotel limit per night London') -> acme-expenses-policy.md#4 (0.502), acme-remote-work-guide.md#5 (0.2)
  step 1: search_docs('receipt taxi') -> acme-expenses-policy.md#7 (0.2), acme-remote-work-guide.md#4 (0.144), acme-expenses-policy.md#6 (0.129)
  step 2: answer
Answer: In London the hotel limit is €250 per night, including taxes [acme-expenses-policy.md#4]. For a €20 taxi you don't need a receipt: receipts are required from €25, and a short note in the expense tool is enough below that [acme-expenses-policy.md#7].
Citations checked: ['acme-expenses-policy.md#4', 'acme-expenses-policy.md#7']; unsupported: none

Question: How many days of parental leave do I get?
  step 1: search_docs('parental leave days') -> acme-expenses-policy.md#7 (0.26), acme-remote-work-guide.md#2 (0.202), acme-expenses-policy.md#3 (0.169)
  step 2: answer
Answer: I couldn't find that in your documents.
Citations checked: none; unsupported: none
```

Notice the second question: search always returns *something* (here, passages that mention "days"). It is the model's job, guided by the system prompt, to notice that none of them answers the question.

### Your own documents

```bash
pip install -r 18-project-3-rag-over-pdfs/requirements.txt     # only if you have PDFs
LLM_PROVIDER=anthropic python 18-project-3-rag-over-pdfs/solution/main.py path/to/folder "What does the contract say about notice periods?"
```

Scanned PDFs contain images, not text, so they extract as empty pages and need OCR first; the loader warns you.

## Test it

```bash
pytest 18-project-3-rag-over-pdfs                          # tests the solution (PDF tests skip without pypdf)
PROJECT_TARGET=starter pytest 18-project-3-rag-over-pdfs   # tests your starter code
```

On Windows PowerShell, set the variable first: `$env:PROJECT_TARGET="starter"`.
