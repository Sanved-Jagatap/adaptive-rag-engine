"""
app/core/config.py

Centralized settings, loaded from environment variables / .env. Everything
else in the app should import `settings` from here rather than reading
os.environ directly — keeps config in one place as the project grows past
Phase 1.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "adaptive-rag-engine"
    app_env: str = "development"
    log_level: str = "INFO"

    # --- FastAPI ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Ollama ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout_seconds: float = 30.0

    # --- Qdrant ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "adaptive_rag"
    postgres_user: str = "raguser"
    postgres_password: str = "change_me_in_dot_env"

    # --- Ingestion ---
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60
    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"

    # --- Embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- CORS ---
    # Comma-separated origins allowed to call the API from a browser (the
    # Next.js frontend, by default at its local dev port). Split into a
    # list in main.py rather than typed as list[str] here, since
    # pydantic-settings needs a validator for env-var list parsing that
    # isn't worth the complexity for a single comma-split.
    cors_allowed_origins: str = "http://localhost:3000"

    # --- Evaluation ---
    # Where scripts/run_evaluation.py saves its results by default, and
    # where GET /evaluation/results reads from — keeping these in sync is
    # what lets "run the eval script" -> "refresh the dashboard" work
    # without extra wiring.
    eval_results_path: str = "experiments/latest_results.json"

    # --- BM25 ---
    bm25_persist_path: str = "data/processed/bm25_corpus.jsonl"

    # --- Reranking ---
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Routing ---
    routing_log_path: str = "experiments/routing_log.jsonl"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    # Cached so Settings() (which reads env/.env) only runs once per process.
    return Settings()


settings = get_settings()
