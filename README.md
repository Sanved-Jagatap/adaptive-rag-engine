# Adaptive RAG Engine

An adaptive Retrieval-Augmented Generation (RAG) system that combines semantic search, BM25 lexical retrieval, hybrid ranking, query rewriting, cross-encoder reranking, grounded generation, and evaluation.

Built to demonstrate practical **AI engineering, retrieval engineering, LLM systems, and RAG evaluation** using a local-first stack.

## Overview

Traditional RAG systems often follow a fixed pipeline:

`Query → Vector Search → Top-K Chunks → LLM → Answer`

Adaptive RAG Engine adds a query-analysis and routing layer to select an appropriate retrieval strategy. Retrieved candidates can be reranked before being passed to a local language model for evidence-grounded generation.

The system also includes citation validation, insufficient-evidence handling, evaluation metrics, a FastAPI backend, and a web interface.

### Highlights

- Adaptive routing across vector, BM25, and hybrid retrieval
- Contextual query rewriting
- Cross-encoder reranking
- Local LLM generation through Ollama
- Citation and evidence validation
- Abstention when retrieved evidence is insufficient
- Retrieval and generation evaluation
- Interactive Next.js frontend
- Docker-based service orchestration
- Automated tests for retrieval, generation, validation, and API behavior

## Architecture

```text
                 Documents
                     |
                     v
           Ingestion and Chunking
                     |
                     v
           Embedding Generation
                     |
                     v
         +-----------------------+
         |    Retrieval Layer    |
         |                       |
         |  Vector Search        |
         |  BM25 Search          |
         |  Hybrid Retrieval     |
         +-----------------------+
                     |
                     v
             Query Routing
                     |
                     v
           Candidate Retrieval
                     |
                     v
          Cross-Encoder Reranking
                     |
                     v
              Evidence Context
                     |
                     v
            Ollama LLM Generation
                     |
                     v
         Citation and Evidence Checks
                     |
                     v
          Answer or Abstention
                     |
                     v
           Evaluation and Metrics
```

The application exposes its backend through FastAPI and provides a web interface for querying the system, inspecting evidence, reviewing evaluation results, and viewing system information.

## Core Features

### 1. Document ingestion

- Document loading and text extraction
- Configurable text chunking
- Chunk metadata and identifiers
- Embedding generation
- Vector indexing
- Support for a local evaluation corpus

The evaluation corpus contains 12 Markdown documents covering topics such as authentication, caching, payment processing, API gateways, rate limiting, database connections, message queues, background jobs, observability, logging, deployment, and security.

### 2. Adaptive retrieval

The engine supports multiple retrieval strategies:

| Strategy | Purpose |
|---|---|
| Semantic vector search | Finds conceptually related evidence |
| BM25 lexical search | Matches keywords, identifiers, and configuration names |
| Hybrid retrieval | Combines semantic and lexical candidate rankings |

Hybrid retrieval uses Reciprocal Rank Fusion (RRF) to combine ranked results.

The routing layer selects a retrieval approach based on query characteristics rather than relying exclusively on vector search.

### 3. Query analysis and rewriting

The system analyzes queries and can rewrite contextual or follow-up questions into retrieval-friendly forms.

For example:

```text
Previous question:
What controls CACHE_TTL_SECONDS?

Follow-up:
What's the default for that setting?

Rewritten query:
What is the default value of CACHE_TTL_SECONDS?
```

This allows follow-up questions to retain relevant context when constructing a retrieval query.

### 4. Cross-encoder reranking

Initial retrieval produces candidate chunks. A cross-encoder reranker then scores candidates against the query to improve their ordering before generation.

```text
Query
  |
  v
Initial retrieval
  |
  v
Candidate chunks
  |
  v
Cross-encoder reranking
  |
  v
Ranked evidence
  |
  v
LLM context
```

### 5. Grounded generation and citation validation

The generation layer uses Ollama to produce answers from retrieved evidence.

The application includes:

- Evidence-grounded answer generation
- Source citation validation
- Rejection of invalid citations
- Confidence and support signals
- Insufficient-evidence handling

When the system cannot establish sufficient support, it can abstain instead of presenting an unsupported answer as fact.

### 6. Evaluation and observability

The project includes a benchmark dataset, retrieval metrics, generation-quality measurements, latency tracking, and a frontend evaluation interface.

Evaluation dimensions include:

- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)
- Faithfulness
- Answer relevance
- Evidence sufficiency
- Retrieval and generation latency
- Token usage

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| Backend API | FastAPI |
| LLM runtime | Ollama |
| Language model | Llama 3.2 |
| Embeddings | Sentence Transformers |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector database | Qdrant |
| Lexical retrieval | BM25 |
| Rank fusion | Reciprocal Rank Fusion |
| Reranking | Cross-encoder |
| Relational database service | PostgreSQL |
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS |
| Testing | pytest |
| Infrastructure | Docker Compose |

## Evaluation Results

The saved evaluation reports compare baseline retrieval with adaptive retrieval across **50 queries**: 15 lexical, 15 semantic, 15 hybrid, and 5 ambiguous.

The following figures come from the saved benchmark report generated on October 1, 2026.

### Retrieval performance

| Metric | Baseline | Adaptive |
|---|---:|---:|
| Recall@5 | 0.930 | 0.930 |
| Precision@5 | 0.188 | 0.188 |
| MRR | 0.892 | 0.930 |

**Observed result:** adaptive retrieval maintained the same Recall@5 and Precision@5 while improving MRR by approximately 0.038, indicating better ranking of relevant evidence within the retrieved results.

### Generation performance

| Metric | Recorded result |
|---|---:|
| Queries evaluated | 50 |
| Sufficient-evidence rate | 100% |
| Average faithfulness | 0.916 |
| Average answer relevance | 0.924 |
| Average total latency | 5.29 seconds |
| Average generation latency | 3.11 seconds |

These values describe the saved October 1 report. They are experimental results, not guarantees for every machine, query, or subsequent run.

### Evaluation limitations

- The benchmark uses a relatively small, project-specific corpus.
- Ambiguous queries have a smaller sample size than other categories.
- Results may vary with model versions, hardware, and service load.
- Aggregate scores do not guarantee that every answer is correct.
- The system can still select one interpretation of an ambiguous question instead of asking the user to clarify.

These limitations are part of the ongoing engineering work rather than evidence that the system is universally reliable.

## Project Structure

```text
adaptive-rag-engine/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── evaluation/
│   ├── generation/
│   ├── ingestion/
│   ├── models/
│   ├── retrieval/
│   ├── routing/
│   └── main.py
├── data/
│   ├── eval_corpus/
│   ├── raw/
│   └── processed/
├── docker/
├── docs/
├── experiments/
│   ├── eval_dataset_v2.jsonl
│   └── latest_results.json
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
├── scripts/
├── tests/
├── .env.example
├── CONTRIBUTING.md
├── docker-compose.yml
├── GETTING_STARTED.md
├── LICENSE
├── pytest.ini
├── README.md
└── requirements.txt
```

Local data, generated logs, caches, and environment files are intentionally excluded where appropriate by `.gitignore`.

## Getting Started

Follow [`GETTING_STARTED.md`](GETTING_STARTED.md) for the repository's detailed setup instructions.

### Prerequisites

- Python and pip
- Docker Desktop with Docker Compose
- Node.js and npm, if running the frontend outside Docker
- Ollama installed on the host machine
- The configured Ollama model available locally

### Configuration

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

Review `.env` and adjust settings for your environment. Never commit the real `.env` file or credentials.

### Start the services

From the project root, use the Docker Compose instructions documented in `GETTING_STARTED.md`.

The configured application uses these default local endpoints:

| Service | URL |
|---|---|
| Backend API | `http://localhost:8000` |
| Frontend | `http://localhost:3001` |
| Qdrant | `http://localhost:6333` |

Ollama runs on the host rather than as a Docker Compose service in the documented configuration.

Verify the actual service status before sending queries. The first model or embedding-model invocation may take longer while required models are loaded.

### Run tests

Activate your Python virtual environment, install the project dependencies if needed, and run:

```powershell
python -m pytest
```

The previously recorded test run passed **99 tests with one warning**. Run the suite again against the version you publish so that the reported result matches the committed code.

## API

The FastAPI backend exposes routes for querying, ingestion, evaluation, health checks, and system information.

The primary operations include:

- Query the RAG engine
- Ingest supported documents
- Run or inspect evaluation
- Check application health
- Inspect system status

Consult the implementation under `app/api/routes/` for the exact request schemas, response formats, and available endpoints.

## Engineering Approach

The project follows an iterative engineering process:

```text
Build
  |
  v
Evaluate
  |
  v
Identify failure modes
  |
  v
Improve retrieval or generation
  |
  v
Evaluate again
```

This process helps distinguish improvements in retrieval quality from changes in generation quality and latency.

## Current Limitations and Future Improvements

- Improve clarification behavior for ambiguous questions.
- Expand the evaluation corpus and benchmark query coverage.
- Evaluate retrieval changes on additional datasets.
- Continue improving the trade-off between retrieval quality and latency.
- Validate behavior across different local models and hardware configurations.
- Add further automated regression checks as new failure cases are discovered.



## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.

## Contributing

Contribution guidelines are available in [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

**Project philosophy:** Build the retrieval system. Measure it. Find where it fails. Improve it. Measure again.
