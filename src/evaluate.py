"""Jour 4 : évaluation du RAG sur 20 questions avec bonnes réponses."""
import json
import sys
import time
import unicodedata
from pathlib import Path

from src import rag
from src.embed import get_collection, load_model
from src.search import search

QUESTIONS_FILE = Path("evaluation/questions.json")
RESULTS_JSON = Path("evaluation/results.json")
RESULTS_MD = Path("evaluation/results.md")
PAUSE_SECONDS = 2   # évite de dépasser les limites de débit de Groq


def normalize(text: str) -> str:
    """Minuscules, sans accents, apostrophes droites : comparaison tolérante."""
    text = text.replace("\u2019", "'").replace("\u00a0", " ").replace("\u202f", " ")
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(text.split())


def matches_all(answer: str, must_contain: list[str]) -> bool:
    """Chaque élément doit apparaître dans la réponse ; "a|b" signifie a OU b."""
    norm = normalize(answer)
    return all(any(normalize(alt) in norm for alt in item.split("|")) for item in must_contain)


def source_ok(sources: list[dict], expected_source: str, expected_pages: list[int]) -> bool:
    return any(s["source"] == expected_source and s["page"] in expected_pages for s in sources)


def diagnose(row: dict) -> str:
    if row["passed"]:
        return "ok"
    if row["type"] == "unanswerable":
        return "réponse inventée (aurait dû refuser)"
    if not row["retrieval_ok"]:
        return "recherche : la bonne page n'est pas dans le top-k"
    if not row["answered"]:
        return "refus à tort (seuil ou LLM)"
    if not row["answer_ok"]:
        return "réponse incorrecte (éléments attendus absents)"
    return "mauvaise source citée"


def evaluate_question(q: dict, model, collection) -> dict:
    result = rag.answer_question(q["question"], model=model, collection=collection)
    row = {
        "id": q["id"], "question": q["question"], "type": q["type"],
        "answer": result["answer"], "answered": result["answered"],
        "best_score": result["best_score"], "sources": result["sources"],
    }
    if q["type"] == "unanswerable":
        row["passed"] = not result["answered"]
    else:
        hits = search(q["question"], k=rag.TOP_K, model=model, collection=collection)
        row["retrieval_ok"] = source_ok(hits, q["source"], q["pages"])
        row["answer_ok"] = result["answered"] and matches_all(result["answer"], q["must_contain"])
        row["source_ok"] = source_ok(result["sources"], q["source"], q["pages"])
        row["passed"] = row["answer_ok"] and row["source_ok"]
    row["reason"] = diagnose(row)
    return row


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["type"] == "answerable"]
    unans = [r for r in rows if r["type"] == "unanswerable"]
    return {
        "total": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "answerable_total": len(ans),
        "answerable_passed": sum(r["passed"] for r in ans),
        "unanswerable_total": len(unans),
        "unanswerable_passed": sum(r["passed"] for r in unans),
        "retrieval_ok": sum(r.get("retrieval_ok", False) for r in ans),
    }


def write_markdown(rows: list[dict], s: dict, path: Path) -> None:
    lines = [
        "# Résultats d'évaluation", "",
        f"**{s['passed']} questions réussies sur {s['total']}**", "",
        f"- Questions avec réponse : {s['answerable_passed']}/{s['answerable_total']} réussies "
        f"(bonne page retrouvée par la recherche : {s['retrieval_ok']}/{s['answerable_total']})",
        f"- Questions sans réponse dans les documents : {s['unanswerable_passed']}/"
        f"{s['unanswerable_total']} correctement refusées", "",
        f"Configuration : modèle `{rag.LLM_MODEL}`, seuil {rag.SCORE_THRESHOLD}, top-k {rag.TOP_K}.", "",
        "| # | Attendu | Question | Résultat | Diagnostic |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        attendu = "réponse" if r["type"] == "answerable" else "refus"
        lines.append(f"| {r['id']} | {attendu} | {r['question']} | "
                     f"{'✅' if r['passed'] else '❌'} | {r['reason']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    questions_path = Path(sys.argv[1]) if len(sys.argv) > 1 else QUESTIONS_FILE
    suffix = "" if questions_path == QUESTIONS_FILE else f"_{questions_path.stem}"
    results_json = Path(f"evaluation/results{suffix}.json")
    results_md = Path(f"evaluation/results{suffix}.md")

    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    model, collection = load_model(), get_collection()

    rows = []
    for q in questions:
        try:
            row = evaluate_question(q, model, collection)
        except Exception as exc:   # limite de débit, réseau...
            row = {"id": q["id"], "question": q["question"], "type": q["type"],
                   "passed": False, "reason": f"erreur : {exc}"}
        rows.append(row)
        print(f"{'OK ' if row['passed'] else 'KO '} #{row['id']:>2} {row['question']}  -> {row['reason']}")
        time.sleep(PAUSE_SECONDS)

    s = summarize(rows)
    results_json.write_text(json.dumps({"summary": s, "rows": rows}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    write_markdown(rows, s, results_md)
    print(f"\n{s['passed']} questions réussies sur {s['total']}")
    print(f"Avec réponse : {s['answerable_passed']}/{s['answerable_total']} "
          f"| Refus corrects : {s['unanswerable_passed']}/{s['unanswerable_total']} "
          f"| Bonne page retrouvée : {s['retrieval_ok']}/{s['answerable_total']}")

if __name__ == "__main__":
    main()