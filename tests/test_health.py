from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "adaptive-rag-engine"


def test_health_returns_200_even_if_dependencies_are_down():
    # In this test environment Ollama/Qdrant aren't running — /health should
    # still return 200 (API is up) and report dependency status in the body,
    # not fail outright. That distinction is the point of this endpoint.
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "ollama" in body["dependencies"]
    assert "qdrant" in body["dependencies"]
