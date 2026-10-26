import sys

from src.embed import get_collection, load_model
from src.search import search

DANS_LE_CORPUS = [
    "Combien d'absences en TP compromettent la validation d'un module ?",
    "Quelle moyenne faut-il pour valider un module en cycle ingénieur ?",
    "Quand le choix des filières du cycle ingénieur est-il arrêté ?",
    "Qu'est-ce que la rétropropagation du gradient ?",
    "Qu'est-ce que le Grid Search ?",
    "Quels sont les événements Scrum ?",
    "Quel est le rôle du Product Owner ?",
]
HORS_CORPUS = [
    "Quelle est la capitale de l'Australie ?",
    "Comment faire un tajine de poulet ?",
    "Quel est le prix du repas à la cantine de l'ENIAD ?",
    "Comment fonctionne un réseau de neurones convolutif ?",
    "Qu'est-ce que le protocole HTTP ?",
    "Quel est le salaire d'un ingénieur IA au Maroc ?",
]

sys.stdout.reconfigure(encoding="utf-8")
model, collection = load_model(), get_collection()
rows = []
for label, questions in (("DANS ", DANS_LE_CORPUS), ("HORS ", HORS_CORPUS)):
    for q in questions:
        score = search(q, k=1, model=model, collection=collection)[0]["score"]
        rows.append((score, label, q))
for score, label, q in sorted(rows, reverse=True):
    print(f"{score:.3f}  {label}  {q}")