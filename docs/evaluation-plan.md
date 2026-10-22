# Evaluation Dataset Construction Plan

Status: **methodology only** — write this now, populate the actual dataset
once Phase 2 (ingestion) and Phase 3 (retrieval) exist. You need a real
chunked corpus before you can hand-label ground truth against it.

## Why plan before data

The query taxonomy below should mirror the router's strategy buckets
(`vector` / `bm25` / `hybrid`) so that once the dataset exists, Recall@5 and
MRR can be sliced by category and directly answer "is the router's routing
decision actually improving retrieval, or would one fixed strategy have
done just as well?" Designing this after the fact means relabeling.

## 1. Query taxonomy

Every query in the eval set gets a `category` label, matched to what the
router is trying to distinguish:

| Category | Example | Should route to |
|---|---|---|
| `lexical` | "What does MAX_RETRY_LIMIT default to?" | bm25 |
| `semantic` | "Why does the payment service retry failed requests?" | vector |
| `hybrid` | "How does payment.retry_config affect retry behavior?" | hybrid |
| `ambiguous` | "What controls that?" (needs prior turn context) | triggers rewrite |

Aim for roughly even coverage across the first three categories, plus a
smaller slice (~10-15%) of `ambiguous` queries specifically to test the
rewrite path — that's the only way to check whether rewriting actually
helps versus just adding LLM-call latency.

## 2. Corpus selection

Don't invent a synthetic corpus — use something real enough that lexical
vs semantic distinctions are meaningful (synthetic toy docs tend to make
every query answerable by any strategy, which defeats the point of the
eval). Two reasonable options:

- **Your own project's docs/codebase** (READMEs, config files, docstrings)
  — free, and you already know the ground truth because you wrote it.
- **A public technical corpus** (e.g. a subset of a well-known open-source
  project's docs) if you want something larger and less self-referential.

Target size to start: **50–200 documents**. Large enough to make retrieval
non-trivial, small enough that you can hand-verify labels without it
becoming a research-scale annotation project.

## 3. Query generation

Two-pass approach, not one:

1. **Hand-write 20–30 seed queries** yourself, one per category above,
   directly against documents you know well. You are the ground truth here
   — no ambiguity about what "relevant" means.
2. **LLM-assisted generation for scale** — for each chunk (or small group of
   chunks), prompt a model to generate a plausible query that chunk would
   answer, tagged with the intended category. This gets you to 100+ queries
   without hand-writing each one, but requires a review pass (see below) —
   LLM-generated queries often skew semantic/vague even when asked for
   lexical ones, so audit the category labels, don't trust them blindly.

Review pass: read every generated query against its source chunk and
confirm (a) the category label is accurate and (b) the query is answerable
from that chunk alone. Discard or fix any that aren't.

## 4. Ground truth labeling

Schema per query:

```json
{
  "query_id": "q_001",
  "query": "What does MAX_RETRY_LIMIT default to?",
  "category": "lexical",
  "relevant_chunk_ids": ["doc_014_chunk_02"],
  "notes": ""
}
```

Start with **binary relevance** (a chunk is either relevant or it isn't) —
graded relevance (fully/partially relevant) adds real labeling overhead for
marginal gain at this dataset size. Revisit only if binary labels prove too
coarse once you're looking at actual Recall@5 numbers.

## 5. Dataset size and stopping point

Rule of thumb: **50–100 labeled queries minimum** for Recall@5/MRR numbers
that aren't dominated by noise from 2-3 unlucky queries. Since you're also
slicing by category (4 buckets), that argues for the higher end — roughly
20-25 queries per category once you're past the initial seed set.

## 6. Storage and versioning

- Store as JSONL at `experiments/eval_dataset.jsonl`, one query object per
  line, matching the schema above.
- Version it (`eval_dataset_v1.jsonl`, `v2.jsonl`, ...) once the corpus or
  labels change — Recall@K numbers from different dataset versions aren't
  comparable, and you'll want that traceable when you write up results.
- Keep it separate from anything used to prompt-engineer the query rewriter
  — if the same queries you tuned the rewrite prompt against also show up
  in your eval set, your "does rewriting help" measurement is contaminated.

## 7. Sequencing

1. **Now:** this plan (done) — informs chunking/routing design decisions.
2. **After Phase 2 (ingestion):** hand-write the 20-30 seed queries against
   real ingested chunks.
3. **After Phase 3 (retrieval + routing wired up):** LLM-assisted expansion
   to 100+, review pass, freeze as `eval_dataset_v1.jsonl`.
4. **Phase 5:** build the Recall@K / MRR computation against the frozen
   dataset, sliced by `category` and by the router's logged `decided_by` /
   `was_rewritten` fields — this is where the routing logger from earlier
   pays off directly.
