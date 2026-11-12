# 06 · Retrieval evaluation, hybrid search and re-ranking

Scores four retrievers on a small labelled eval set (12 queries, graded relevance) with recall@k, precision@k, MRR and nDCG@k:

- **BM25** keyword search;
- **vector** search with a toy character-trigram embedding;
- **hybrid**: both rankings merged with reciprocal rank fusion (RRF);
- **hybrid + re-rank**: the top 10 re-scored by a function that reads the query and each document together, as a cross-encoder does.

Used in [6.5 Re-ranking & retrieval evaluation](../../docs/06-rag-for-agents/06.5-re-ranking-and-retrieval-evaluation.md). Everything is pure Python. Real systems use an embedding model for the vector side and a trained re-ranker model; the toy versions here show the plumbing and the metrics, not realistic quality.

## Run it

```bash
cd examples
python 06-retrieval-eval/main.py
```

Output:

```text
Retriever                   recall@3   precision@3           MRR        nDCG@3
BM25                            0.79          0.33          0.79          0.77
vector (trigram toy)            0.92          0.39          0.96          0.92
hybrid (RRF)                    0.92          0.39          0.92          0.89
hybrid + re-rank                0.96          0.42          1.00          0.98

Top 3 per retriever:
  'cancelling my subscription'  (relevant: {'cancel': 2, 'refunds': 1})
    BM25                   []
    vector (trigram toy)   ['cancel', '2fa', 'sso']
    hybrid (RRF)           ['cancel', '2fa', 'sso']
    hybrid + re-rank       ['cancel', '2fa', 'sso']
  'how long are backups kept'  (relevant: {'backups': 2})
    BM25                   ['restore', 'backups']
    vector (trigram toy)   ['backups', 'restore', 'err-e5003']
    hybrid (RRF)           ['restore', 'backups', 'err-e5003']
    hybrid + re-rank       ['backups', 'restore', 'err-e5003']
```

What to notice:

- BM25 finds nothing for *"cancelling my subscription"*: no exact word matches *"Cancel plan"* or *"Cancellation"*. The trigram vectors catch the shared spelling.
- On this tiny set, hybrid (RRF) scores slightly **below** the vector toy: for *"how long are backups kept"* BM25 was confidently wrong and dragged `restore` to the top. Fusion is not automatically better. Measure on your own data.
- The re-ranker fixes that order, and lifts every metric.
- precision@3 can't go above about 0.4 here because most queries have only one relevant document.

## Test it

```bash
pytest 06-retrieval-eval
```

## Things to try

- Change `k` in `main()` to 1 and to 5. Which metrics move, and which can't?
- Add a query with no relevant documents. What should each metric do? (Look at how `recall_at_k` handles it.)
- Change the RRF constant `k=60` to `k=1`. Does hybrid get better or worse here?
