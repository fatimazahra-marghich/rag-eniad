from types import SimpleNamespace

import groq
import httpx
import pytest
from fastapi.testclient import TestClient

from src import api, rag

# Sans "with", le lifespan (chargement du modèle) n'est pas lancé : tests rapides.
client = TestClient(api.app)

FAKE_ANSWER = {
    "answer": "12/20 pour le CI [1].", "answered": True,
    "sources": [{"source": "reglement_eniad.pdf", "page": 3, "score": 0.9}], "best_score": 0.9,
}


@pytest.fixture(autouse=True)
def fake_state():
    api.app.state.model = object()
    api.app.state.collection = SimpleNamespace(count=lambda: 198)


def test_health_reports_index_size():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["chunks"] == 198


def test_ask_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(rag, "answer_question", lambda *a, **k: FAKE_ANSWER)
    r = client.post("/ask", json={"question": "Quelle moyenne pour valider ?"})
    assert r.status_code == 200
    assert r.json()["sources"][0]["page"] == 3


def test_ask_rejects_too_short_question():
    assert client.post("/ask", json={"question": "a"}).status_code == 422


def test_ask_rejects_too_long_question():
    assert client.post("/ask", json={"question": "x" * 501}).status_code == 422


def test_ask_maps_connection_error_to_502(monkeypatch):
    def boom(*a, **k):
        raise groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))
    monkeypatch.setattr(rag, "answer_question", boom)
    r = client.post("/ask", json={"question": "Quelle moyenne ?"})
    assert r.status_code == 502 and "gsk_" not in r.text


def test_ask_maps_rate_limit_to_429(monkeypatch):
    def boom(*a, **k):
        req = httpx.Request("POST", "https://api.groq.com")
        raise groq.RateLimitError("limit", response=httpx.Response(429, request=req), body=None)
    monkeypatch.setattr(rag, "answer_question", boom)
    assert client.post("/ask", json={"question": "Quelle moyenne ?"}).status_code == 429


def test_agent_endpoint_returns_steps(monkeypatch):
    fake = {"answer": "12 [1]", "answered": True,
            "sources": [{"source": "reglement_eniad.pdf", "page": 3, "score": 0.9}],
            "steps": [{"tool": "calculate", "arguments": {"expression": "(11+13+12)/3"}, "result": "12.0"}]}
    monkeypatch.setattr(api, "run_agent", lambda *a, **k: fake)
    r = client.post("/agent", json={"question": "Moyenne de 11, 13 et 12 ?"})
    assert r.status_code == 200 and r.json()["steps"][0]["tool"] == "calculate"