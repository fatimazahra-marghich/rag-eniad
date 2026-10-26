from src.search import search

hits = search("Combien d'absences en TP compromettent la validation d'un module ?", k=10)
for i, h in enumerate(hits, 1):
    found = "plus d" in h["text"] and "Travaux Pratiques" in h["text"]
    print(i, h["score"], "p.", h["page"], "<-- règle TP" if found else "")