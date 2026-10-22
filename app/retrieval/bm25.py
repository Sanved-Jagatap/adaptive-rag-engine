"""
app/retrieval/bm25.py

BM25 lexical retrieval via rank-bm25. Unlike the embedder/reranker, this
has zero external dependencies — no model download, no network — so it's
directly testable with the real implementation, not a stub.

Index lives in-process (rank_bm25.BM25Plus rebuilds from a token corpus
held in memory) with optional JSON persistence so the corpus survives a
process restart without needing Postgres wired up yet. This is a known
scaling limit — see the module-level note under "Known limitation" below —
acceptable for Phase 3, worth revisiting in Phase 6 (Productization) if the
corpus grows past what fits comfortably in memory.

Uses BM25Plus rather than the more common BM25Okapi: classical BM25's IDF
formula (log((N-n+0.5)/(n+0.5))) hits exactly zero whenever a term's
document frequency is exactly half the corpus, and goes negative above
that — which silently zeroes out otherwise-relevant matches. This isn't
just a small-corpus edge case (it surfaced immediately in a 2-chunk unit
test) — it can recur at any corpus size whenever a term's df lands near
N/2. BM25Plus adds a small constant (delta) to the score so it can never
collapse to zero regardless of document frequency.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Plus

from app.models.schemas import Chunk
from app.retrieval.types import RetrievedChunk

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


class BM25Retriever:
    """
    Known limitation: single-process, in-memory index rebuilt on every
    index_chunks() call. Fine for a portfolio-scale corpus (hundreds to a
    few thousand chunks); a real lexical search backend (Elasticsearch/
    OpenSearch, or Qdrant's own sparse-vector support) is the right call
    if this ever needs to scale or run across multiple API instances.
    """

    def __init__(self, persist_path: str | Path | None = None):
        self.persist_path = Path(persist_path) if persist_path else None
        self._chunks: dict[str, Chunk] = {}
        self._bm25: BM25Plus | None = None

        if self.persist_path and self.persist_path.exists():
            self._load_from_disk()
            self._rebuild_index()

    def index_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
        self._rebuild_index()
        if self.persist_path:
            self._save_to_disk()

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if self._bm25 is None or not self._chunks:
            return []

        chunk_ids = list(self._chunks.keys())
        scores = self._bm25.get_scores(_tokenize(query))

        ranked = sorted(zip(chunk_ids, scores), key=lambda x: x[1], reverse=True)
        results = []
        for chunk_id, score in ranked[:top_k]:
            if score <= 0:
                continue  # BM25 score of 0 means no term overlap — not a real match
            results.append(RetrievedChunk(chunk=self._chunks[chunk_id], score=float(score)))
        return results

    def _rebuild_index(self) -> None:
        corpus = [_tokenize(chunk.text) for chunk in self._chunks.values()]
        self._bm25 = BM25Plus(corpus) if corpus else None

    def _save_to_disk(self) -> None:
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self.persist_path.open("w") as f:
            for chunk in self._chunks.values():
                f.write(chunk.model_dump_json() + "\n")

    def _load_from_disk(self) -> None:
        with self.persist_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                chunk = Chunk(**data)
                self._chunks[chunk.chunk_id] = chunk
