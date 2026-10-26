# Notes de développement

## Jour 1 : ingestion et chunking

- Corpus : 6 PDF (règlement ENIAD, 2 chapitres Agile, 3 chapitres Deep Learning), 198 chunks, médiane 455 caractères.
- Extraction : pypdf collait des mots (« Réseauxde », « ouplus »). Après comparaison sur mes PDF, je suis passée à PyMuPDF.
- Bruit : en-tête et pied de page répétés sur chaque page du règlement, numéros de diapositive collés au texte. Solution : suppression des lignes présentes sur au moins 40 % des pages et des lignes qui sont des numéros de page.
- Chunks de titres seuls (diapositives dont le contenu est une image) : filtrés sous 80 caractères.
- Limites connues : tableaux aplatis (perte du lien entre colonnes), schémas et formules en image non extraits, pas d'OCR.
- À vérifier au jour 4 : taille 800 / chevauchement 150, via le taux de réussite sur les 20 questions.

## Jour 2 : embeddings et base vectorielle

- Modèle : intfloat/multilingual-e5-small (384 dimensions, contexte 512 tokens, multilingue). J'ai écarté paraphrase-multilingual-MiniLM, qui tronque à 128 tokens, et bge-m3, trop lourd pour le niveau gratuit de Cloud Run.
- Base vectorielle : Chroma (embarquée, sans serveur), distance cosinus, score = 1 - distance. pgvector aurait demandé un Postgres payant.
- Préfixes « query: » et « passage: » exigés par le modèle e5.
- Scores observés : questions dans le corpus 0.87 à 0.90, question hors corpus 0.75. Les scores e5 sont comprimés (0.7 à 1.0) : le seuil doit être calibré, pas deviné.
- Défaut corrigé : accents LaTeX séparés de la lettre dans un cours (« ´eviter », « probl`eme »), réparés dans clean().
- Constats à tester au jour 4 : le nombre de résultats k compte (5 événements Scrum mais k=3), et une page de titre peut remonter comme chunk de bruit (score 0.853 sur la rétropropagation).
- À vérifier : la règle « plus d'une absence en TP compromet la validation » est-elle dans le top 4 ? (résultat de check.py : à compléter)

## Jour 3 : RAG complet (Groq, sources, « je ne sais pas »)

- Modèle : openai/gpt-oss-120b (les modèles Llama de Groq ont été arrêtés le 16 août 2026), configurable via la variable GROQ_MODEL.
- Calibration du seuil sur 13 questions : dans le corpus 0.874 à 0.905, hors corpus 0.752 à 0.872.
- Seuil provisoire 0.85 : bloque 5 questions hors sujet sur 6 avant tout appel au LLM.
- La question sur les réseaux convolutifs (0.872) passe le seuil, mais le LLM refuse de répondre : le seuil seul ne suffit pas, d'où deux garde-fous (seuil de similarité + consigne du prompt).
- Sources : seuls les passages réellement cités ([1], [2]...) sont affichés. Température 0 pour des réponses reproductibles.
- Le prompt précise que les passages sont des données et non des instructions (protection contre l'injection de prompt).
- À mesurer au jour 4 : refus à tort (seuil trop haut) et réponses inventées (seuil trop bas).