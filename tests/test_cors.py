from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_headers_present_for_allowed_origin():
    # Simulates what a browser's preflight OPTIONS request checks before
    # allowing the frontend's fetch() call through. Without CORSMiddleware
    # configured, this header would be absent and every browser-based
    # request from the frontend would fail silently with a CORS error.
    resp = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3001"


def test_cors_headers_absent_for_disallowed_origin():
    resp = client.options(
        "/query",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.example.com"
