import json
from types import SimpleNamespace

import src.agent as agent


def fake_client(responses):
    it = iter(responses)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: next(it))))


def tool_call(name, args, call_id="c1"):
    tc = SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(args)))
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))])


def final(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))])


def fake_hits(*a, **k):
    return [{"text": "Le module est validé si la moyenne est au moins 12/20 pour le CI.",
             "source": "reglement_eniad.pdf", "page": 3, "score": 0.9}]


def test_calculate_basic():
    assert agent.calculate("(11+13+12)/3") == "12.0"
    assert agent.calculate("2**3 + 1") == "9"
    assert agent.calculate("12,5 * 2") == "25.0"


def test_calculate_rejects_code():
    assert agent.calculate("__import__('os').system('echo x')").startswith("Erreur")
    assert agent.calculate("open('secret.txt')").startswith("Erreur")
    assert agent.calculate("9**9**9").startswith("Erreur")


def test_calculate_division_by_zero():
    assert agent.calculate("1/0") == "Erreur : division par zéro"


def test_search_tool_filters_below_threshold(monkeypatch):
    monkeypatch.setattr(agent, "search", lambda *a, **k: [{"text": "x", "source": "a.pdf", "page": 1, "score": 0.5}])
    retrieved = []
    assert "Aucun passage" in agent.search_documents("q", retrieved, None, None)
    assert retrieved == []


def test_agent_uses_both_tools_then_answers(monkeypatch):
    monkeypatch.setattr(agent, "search", fake_hits)
    client = fake_client([
        tool_call("search_documents", {"query": "moyenne module CI"}, "c1"),
        tool_call("calculate", {"expression": "(11+13+12)/3"}, "c2"),
        final("Moyenne 12.0, soit le minimum de 12/20 [1] : module validé."),
    ])
    r = agent.run_agent("Notes 11, 13, 12 : module validé en CI ?", model=object(), collection=object(), client=client)
    assert [s["tool"] for s in r["steps"]] == ["search_documents", "calculate"]
    assert r["answered"] is True and r["sources"][0]["page"] == 3


def test_agent_refusal_has_no_sources(monkeypatch):
    monkeypatch.setattr(agent, "search", lambda *a, **k: [])
    client = fake_client([tool_call("search_documents", {"query": "x"}), final(agent.rag.NO_ANSWER)])
    r = agent.run_agent("Question hors sujet ?", model=object(), collection=object(), client=client)
    assert r["answered"] is False and r["sources"] == []


def test_agent_stops_after_max_steps(monkeypatch):
    monkeypatch.setattr(agent, "search", fake_hits)
    client = fake_client([tool_call("search_documents", {"query": "x"}, f"c{i}") for i in range(10)])
    r = agent.run_agent("boucle ?", model=object(), collection=object(), client=client)
    assert len(r["steps"]) == agent.MAX_STEPS and r["answered"] is False


def test_unknown_tool_and_bad_arguments():
    assert "inconnu" in agent.execute_tool("rm_rf", "{}", [], None, None)[1]
    assert "illisibles" in agent.execute_tool("calculate", "pas du json", [], None, None)[1]