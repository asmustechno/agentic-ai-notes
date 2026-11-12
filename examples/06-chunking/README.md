# 06 · Chunking strategies

Splits one small handbook five ways (fixed-size with overlap, sentence packing, semantic breaks, by headings, parent-child), indexes each, and checks whether the top-ranked chunk contains the answer to six questions. Used in [6.3 Chunking strategies](../../docs/06-rag-for-agents/06.3-chunking-strategies.md).

The "embedding" is a tiny hashed bag-of-words in pure Python, so it runs offline with no extra packages. Real systems use an embedding model ([6.2](../../docs/06-rag-for-agents/06.2-embeddings-and-vector-databases.md)). No LLM is involved: chunking happens before the model sees anything.

## Run it

```bash
cd examples
python 06-chunking/main.py
```

Output:

```text
Strategy                             chunks avg words top-1 hits
fixed-size (40 words, 10 overlap)         7      35.9      5/6
sentence-packed (<= 40 words)             5      34.6      5/6
semantic (break on topic shift)           8      21.6      4/6
by headings                               6      31.2      6/6
parent-child                             20      32.5      6/6

Misses:
  fixed-size (40 words, 10 overlap): How long are backups kept on the Pro plan?
  sentence-packed (<= 40 words): What are the live chat support hours?
  semantic (break on topic shift): What are the live chat support hours?
  semantic (break on topic shift): How much does the Pro plan cost?

Top chunk for 'How long are backups kept on the Pro plan?':
  fixed-size (40 words, 10 overlap) (score 0.37): free. It includes one project and 10,000 API requests per month. Backups are kept for 7 days. Support is by em...
  by headings (score 0.46): Plans > Pro plan: The Pro plan costs $49 per month. It includes ten projects and 1,000,000 API requests per mo...
```

Notice the first miss: the fixed-size chunk that wins for *"How long are backups kept on the Pro plan?"* holds the **Starter** plan's "Backups are kept for 7 days", followed by the "Pro plan" heading. The chunk with the right answer (30 days) starts after that heading, so nothing in it says "Pro". A model would confidently answer "7 days". Keeping the heading path in each chunk fixes it.

## Test it

```bash
pytest 06-chunking
```

## Things to try

- Change `fixed_size` to `size=60, overlap=20`. Does the Pro-plan miss go away? What happens to the number of chunks?
- Remove the heading prefix from the children in `parent_child` (embed only the sentence). Which question breaks, and why?
- Add your own question to `QUESTIONS` whose answer spans two sections.
