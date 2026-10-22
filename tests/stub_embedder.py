"""
tests/stub_embedder.py

Deterministic, network-free embedder for tests. Hashes each word into a
fixed-size vector and sums — not semantically meaningful, but stable
(same text always produces the same vector) and enough to test the
plumbing (index -> search -> get results back) without downloading real
model weights. Real semantic quality is a sentence-transformers concern,
not something this test double needs to approximate.
"""

import hashlib

DIM = 384


class StubEmbedder:
    dimension = DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * DIM
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode()).digest()
            for i in range(DIM):
                vector[i] += digest[i % len(digest)] / 255.0
        # normalize so vectors are comparable in magnitude
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]
