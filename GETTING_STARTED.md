# Getting Started

Covers what's built through **Phase 6** (the whole roadmap): repo
scaffolding, FastAPI backend, Docker environment, Ollama integration,
document ingestion, embedding generation, Qdrant vector indexing, BM25
lexical retrieval, hybrid retrieval (Reciprocal Rank Fusion), cross-encoder
reranking, adaptive query routing, reliability features (citations,
evidence validation, confidence scoring, insufficient-evidence handling),
a full evaluation harness (Recall@K/Precision@K/MRR, faithfulness/relevance
via LLM-as-judge, latency/token measurement, baseline-vs-adaptive
comparison), a Next.js query console with source viewer and query history,
an evaluation dashboard, structured logging, and production-hardened
Docker (non-root users, healthchecks).

## Local dev (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

Note: `.env.example` defaults `OLLAMA_HOST`/`QDRANT_HOST` to Docker service
names (`http://ollama:11434` / `qdrant`). For local dev without Docker,
override them in your `.env` to `http://localhost:11434` and `localhost`.

**First real run will be slow** — `sentence-transformers` downloads the
embedding model and the cross-encoder reranker model from Hugging Face the
first time they're used (needs network access; cached locally after that).
See `docker/Dockerfile` for why `torch` is installed as a separate,
CPU-only step first — without that, pip resolves the full CUDA/GPU build
and pulls several GB of unused NVIDIA packages.

## Docker Compose (API + Qdrant + Postgres + Ollama)

```bash
cp .env.example .env
docker compose up --build
```

First run only — pull a model into the Ollama container:

```bash
docker compose exec ollama ollama pull llama3.1
```

### Alternative: Ollama already running natively on the host

If Ollama is already installed and running directly on your machine
(common on Windows, or if another tool already uses it) rather than as a
container, you don't need the `ollama` service in `docker-compose.yml` at
all. Instead:

1. Remove (or comment out) the `ollama` service block and drop `ollama`
   from `api`'s `depends_on`.
2. In `.env`, point at the host's Ollama instead of the Docker service name:
   ```
   OLLAMA_HOST=http://host.docker.internal:11434
   OLLAMA_MODEL=<model name as shown by `ollama list` on the host>
   ```
   `host.docker.internal` is Docker's standard hostname for reaching the
   host machine from inside a container (works on Docker Desktop for
   Windows/Mac; on native Linux Docker you may need `--add-host` or the
   host's actual LAN IP instead).
3. If another local service already occupies port 3000 (e.g. Grafana),
   change the frontend's published port and matching CORS origin:
   ```yaml
   # docker-compose.yml, frontend service
   ports:
     - "3001:3000"
   ```
   ```
   # .env
   CORS_ALLOWED_ORIGINS=http://localhost:3001
   ```

This is a real, verified deployment pattern (confirmed working end-to-end
against `llama3.2:latest` running natively on Windows) — just not the
default, since baking a host-specific hostname and an alternate port into
the shared `docker-compose.yml` would break the normal all-in-Docker setup
for anyone else running this without those constraints.

Then try the pipeline end to end:

```bash
curl -X POST http://localhost:8000/ingest
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What controls the payment retry limit?"}'
```

`/ingest` reads every file in `data/raw/` (drop your own `.pdf`/`.md`/`.txt`
files there — `sample.md` is included as a starting point), chunks and
indexes them into both Qdrant (vector) and the BM25 lexical index.

`/query` is the fully adaptive path:
1. `query_router.py` decides `vector` / `bm25` / `hybrid`, and whether the
   query needs rewriting (rule-based fast path, LLM fallback for ambiguous
   queries).
2. Retrieves with whichever strategy was chosen.
3. Reranks with the cross-encoder if the router says to.
4. Generates a structured answer (JSON: answer + cited sources + a
   sufficient-evidence claim).
5. Validates the claimed citations against what was actually retrieved —
   catches hallucinated source numbers.
6. Scores confidence from citation coverage and (when available) the
   cross-encoder score.
7. Guarantees the final `answer` text and `sufficient_evidence` flag can
   never contradict each other.

### `/query` response shape

```json
{
  "answer": "...",
  "cited_sources": [1, 2],
  "invalid_citations": [],
  "sufficient_evidence": true,
  "confidence_level": "high",
  "citation_coverage": 1.0,
  "sources": [{"chunk_id": "...", "text": "...", "score": 0.82, "rerank_score": 3.1}],
  "strategy": "hybrid",
  "decided_by": "rule",
  "was_rewritten": false,
  "used_query": "..."
}
```

`strategy`/`decided_by`/`was_rewritten` aren't just debugging fields — this
is exactly what the Phase 5 evaluation needs to compare baseline vs
adaptive retrieval and to check whether query rewriting actually helps.

## Tests

```bash
pytest tests/ -v
```

49 tests, all runnable with **no external services and no network access**:
- Loader, chunker: pure logic, no dependencies.
- Vector retrieval: Qdrant in-memory mode + deterministic stub embedder.
- BM25: real `rank-bm25` (`BM25Plus`), no network dependency at all.
- Hybrid: RRF fusion logic, plus an end-to-end index+search test.
- Reranker: mocks only the model boundary (`CrossEncoder.predict`), so the
  real sorting/scoring logic in the module is actually exercised.
- Generator / validator / confidence / finalize: structured-output parsing,
  malformed-JSON fallback, hallucinated-citation detection, confidence
  scoring branches, answer/flag consistency.
- `/query` integration tests: exercise the full router → retrieval →
  rerank → generation → validation → confidence chain via FastAPI
  dependency overrides — the only tests that verify the wiring itself,
  not just each module in isolation.
- Health endpoint: confirms `/health` returns `200` and reports dependency
  status even when Ollama/Qdrant aren't reachable, rather than crashing.

## Manual ingestion smoke test

```bash
python scripts/smoke_test_ingestion.py
```

Loads and chunks `data/raw/sample.md` and prints the resulting chunks —
load/chunk only, no embedding (works fully offline).

## What's not built (out of scope for the current roadmap)

- Postgres is running in Docker Compose but nothing writes to it yet — no
  SQLAlchemy models or migrations exist. Every piece of metadata the app
  actually needs (chunk text, doc_id, routing decisions, eval results) is
  already served from Qdrant payloads, the BM25 in-memory index, or flat
  files — Postgres was scaffolded for future structured storage (e.g. a
  query history table shared across browsers, user accounts) that the
  current single-user, file-backed design doesn't yet need.
- No authentication/multi-user support — the query console and its
  localStorage-backed history are single-user by design (see
  `frontend/lib/history.ts`).
- No CI pipeline (GitHub Actions or similar) running `pytest`/`npm run
  build` automatically on push.

## Known limitations worth knowing about

- Chunking uses a whitespace-based word-count approximation instead of a
  real tokenizer (see `app/ingestion/chunker.py` docstring).
- `load_directory()` is non-recursive.
- No structure-aware chunking (headings/sections respected) yet.
- `/ingest` is synchronous/blocking — fine for a handful of files, worth
  moving to a background task queue before ingesting anything large.
- Confidence scoring intentionally does NOT average raw retrieval scores
  across strategies (vector cosine, BM25, rerank scores aren't on
  comparable scales) — see `app/generation/confidence.py` docstring for the
  reasoning. No calibrated numeric threshold exists yet either; that's an
  evaluation-driven task once the dataset is larger, not something to
  guess at now.
- Qdrant point IDs are derived from a hash of `chunk_id` (see
  `_stable_point_id` in `app/core/qdrant_store.py`) so re-ingesting the
  same file upserts rather than duplicates — collision risk is
  astronomically low at this dataset size, worth knowing about if the
  corpus ever gets large.

## Evaluation (Phase 5)

```bash
python scripts/run_evaluation.py --stub          # sanity-check the pipeline, no network needed
python scripts/run_evaluation.py                 # real run: needs sentence-transformers model + Ollama running
python scripts/run_evaluation.py --output experiments/results.json
```

Ingests `data/raw/` fresh into an in-memory index (independent of whatever's
in your Docker Compose Qdrant), runs `experiments/eval_dataset_v1.jsonl`
(15 hand-written queries across lexical/semantic/hybrid/ambiguous
categories) against both vector-only baseline and full adaptive retrieval,
and prints:
- Recall@K / Precision@K / MRR, baseline vs adaptive, overall and by category
- Generation quality: sufficient-evidence rate, faithfulness/relevance
  (LLM-as-judge), token usage, per-stage latency

**`--stub` mode** uses a deterministic hash-based embedder, a pass-through
reranker, and canned LLM responses — proves the whole pipeline runs
correctly with zero network calls, but the numbers are not meaningful
(nothing is actually being semantically judged). Use it to verify the
machinery, not to report results. Real numbers require the default mode
(network for model downloads, Ollama running).

Corpus is currently only 3 short single-chunk documents, so Recall@5 is
trivially 1.0 for everything at that scale — per `docs/evaluation-plan.md`,
the dataset needs expanding (50+ queries, larger corpus) before these
numbers say anything meaningful about baseline vs adaptive performance.

## Evaluation dashboard (Phase 6)

Visit `http://localhost:3000/evaluation` after running
`python scripts/run_evaluation.py` — it reads whatever the script last
saved to `experiments/latest_results.json` via `GET /evaluation/results`.
Shows baseline-vs-adaptive Recall@K/Precision@K/MRR, the category
breakdown, and generation quality (faithfulness/relevance/latency) when
available. A clear banner appears if the results came from `--stub` mode.

## Docker hardening (Phase 6)

Both Dockerfiles run as a non-root user and define a `HEALTHCHECK`.
`docker-compose.yml` adds healthchecks for the third-party images
(Postgres via `pg_isready` — standard for that image; Qdrant via a
bash `/dev/tcp` TCP check, since that image has no curl/wget; Ollama via
`ollama list`, using its own binary) and `depends_on: condition:
service_healthy`, so `api` actually waits for Qdrant/Postgres/Ollama to be
ready, not just started.

**Caveats worth knowing, since none of this was verified against a real
Docker daemon** (not available in the environment this was built in):
- The Qdrant healthcheck assumes `bash` is present in that image (debian-
  slim base, typically true, but unverified here).
- `api`'s Dockerfile does `chown -R appuser:appuser /app` for files copied
  during the build, but `docker-compose.yml` also bind-mounts `./app` over
  part of that directory for local dev live-reload — bind-mounted files
  keep their *host* ownership/permissions, not the container's `chown`.
  In practice this is usually fine since source files are normally
  world-readable, but if `api` fails to start with a permission error
  after this change, that bind mount is the first thing to check.
- First real `docker compose build` after these changes is worth watching
  closely for exactly these reasons.
