import asyncio

from app.core.ollama_client import OllamaClient
from app.generation.generator import build_prompt, generate_answer
from app.ingestion.loader import load_directory
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import SentenceTransformerEmbedder
from app.retrieval.vector import VectorRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.core.qdrant_store import QdrantStore


QUERIES = [
    "Why can caching reduce database load?",
    "Why does a shorter cache lifetime improve freshness but increase database traffic?",
    "Why does exponential backoff help protect an overloaded dependency?",
    "Why can a local in-memory rate limiter be inconsistent across application instances?",
    "Why can an excessively large database connection pool be harmful?",
    "Why are traces useful when a request crosses multiple services?",
    "Why should production logs avoid recording authentication tokens?",
    "Why should secrets be kept out of source control?",
]


async def main():
    documents = load_directory("data/eval_corpus")

    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    embedder = SentenceTransformerEmbedder()

    store = QdrantStore(
        collection_name="semantic_citation_test",
        vector_size=embedder.dimension,
        in_memory=True,
    )

    retriever = VectorRetriever(
        embedder=embedder,
        store=store,
    )

    retriever.index_chunks(all_chunks)

    reranker = CrossEncoderReranker()
    client = OllamaClient()

    for query in QUERIES:
        print("\n" + "=" * 80)
        print("QUERY:", query)
        print("=" * 80)

        retrieved = retriever.search(query, top_k=5)

        retrieved = reranker.rerank(
            query,
            retrieved,
        )[:5]

        print("\nTop sources:")
        for i, r in enumerate(retrieved, 1):
            print(
                f"  Source {i}: "
                f"{r.chunk.chunk_id} "
                f"(rerank={r.rerank_score:.3f})"
            )

        result = await generate_answer(
            query,
            retrieved,
            client,
        )

        print("\nANSWER:")
        print(result.answer)

        print("CITED SOURCES:", result.cited_sources)
        print("SUFFICIENT EVIDENCE:", result.sufficient_evidence)


if __name__ == "__main__":
    asyncio.run(main())
