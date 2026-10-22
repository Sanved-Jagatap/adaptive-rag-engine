import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_evaluation_results_404_when_no_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eval_results_path", str(tmp_path / "does_not_exist.json"))
    resp = client.get("/evaluation/results")
    assert resp.status_code == 404
    assert "run_evaluation.py" in resp.json()["detail"]


def test_evaluation_results_returns_saved_json(tmp_path, monkeypatch):
    results_path = tmp_path / "results.json"
    payload = {"k": 5, "baseline": {"overall": {"recall_at_k": 0.8}}, "adaptive": {"overall": {"recall_at_k": 0.9}}}
    results_path.write_text(json.dumps(payload))
    monkeypatch.setattr(settings, "eval_results_path", str(results_path))

    resp = client.get("/evaluation/results")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_evaluation_results_500_on_corrupted_json(tmp_path, monkeypatch):
    results_path = tmp_path / "corrupted.json"
    results_path.write_text("{not valid json")
    monkeypatch.setattr(settings, "eval_results_path", str(results_path))

    resp = client.get("/evaluation/results")
    assert resp.status_code == 500
