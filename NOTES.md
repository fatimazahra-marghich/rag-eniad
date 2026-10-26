# Notes de développement

## Jour 1 : ingestion et chunking

- Corpus : 6 PDF (règlement ENIAD, 2 chapitres Agile, 3 chapitres Deep Learning), 198 chunks, médiane 455 caractères.
- Extraction : pypdf collait des mots (« Réseauxde », « ouplus »). Après comparaison sur mes PDF, je suis passée à PyMuPDF.
- Bruit : en-tête et pied de page répétés sur chaque page du règlement, numéros de diapositive collés au texte. Solution : suppression des lignes présentes sur au moins 40 % des pages et des lignes qui sont des numéros de page.
- Chunks de titres seuls (diapositives dont le contenu est une image) : filtrés sous 80 caractères.
- Limites connues : tableaux aplatis (perte du lien entre colonnes), schémas et formules en image non extraits, pas d'OCR.
- À vérifier au jour 4 : taille 800 / chevauchement 150, via le taux de réussite sur les 20 questions.
## jour 2
La question sur les absences en TP est à vérifier. Ton top 3 contient des passages sur les absences, mais je ne vois pas la règle exacte (« l’absence à plus d’une séance de TP compromet la validation »). Elle est peut-être dans un autre chunk que le top 3. Crée check.py à la racine, lance python check.py, puis colle-moi le résultat :
python
from src.search import search

hits = search("Combien d'absences en TP compromettent la validation d'un module ?", k=10)
for i, h in enumerate(hits, 1):
    found = "plus d" in h["text"] and "Travaux Pratiques" in h["text"]
    print(i, h["score"], "p.", h["page"], "<-- règle TP" if found else "")

Ça nous dit si la règle est au rang 1, 2, 3… ou absente. C’est le même type de test que fera ton évaluation du jour 4.

Le nombre de résultats k compte. Pour « Quels sont les événements Scrum ? », il y a 5 événements mais k=3 en renvoie 3. Le choix de k sera à tester.
Un chunk de bruit apparaît au rang 3 de la rétropropagation : la page de titre (« Pr S. MHAMMEDI 2025-2026 Chapitre2… »). Il atteint 0.853 sans rien contenir d’utile. Les pages de titre pourront être filtrées plus tard si l’évaluation montre qu’elles gênent.
