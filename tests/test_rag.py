from types import SimpleNamespace

import src.rag as rag


def fake_hits(score):
    return [{"text": "Le module est validé si la moyenne est au moins 12/20.",
             "source": "reglement.pdf", "page": 3, "score": score}]


def fake_client(text):
    def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_cited_indices_ignores_invalid():
    assert rag.cited_indices("Oui [1] et [3], pas [9]", 3) == [1, 3]


def test_is_refusal():
    assert rag.is_refusal("Je ne sais pas : rien dans les documents.")
    assert not rag.is_refusal("La moyenne est 12/20 [1].")


def test_build_messages_contains_source_and_page():
    msgs = rag.build_messages("Quelle moyenne ?", fake_hits(0.9))
    assert "reglement.pdf" in msgs[1]["content"] and "page 3" in msgs[1]["content"]


def test_below_threshold_never_calls_llm(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda *a, **k: fake_hits(0.50))

    def boom(**kwargs):
        raise AssertionError("le LLM ne doit pas être appelé")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=boom)))
    r = rag.answer_question("hors sujet", client=client)
    assert r["answered"] is False and r["sources"] == []


def test_answer_returns_cited_sources(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda *a, **k: fake_hits(0.95))
    r = rag.answer_question("q", client=fake_client("12/20 [1]"))
    assert r["answered"] is True
    assert r["sources"][0]["source"] == "reglement.pdf" and r["sources"][0]["page"] == 3


def test_llm_refusal_drops_sources(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda *a, **k: fake_hits(0.95))
    r = rag.answer_question("q", client=fake_client("Je ne sais pas : absent."))
    assert r["answered"] is False and r["sources"] == []