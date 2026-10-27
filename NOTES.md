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
- Vérification (check.py) : la règle « plus d'une absence en TP compromet la validation » remonte au rang 1 (score 0.889), le retrieval est donc correct sur cette question.

## Jour 3 : RAG complet (Groq, sources, « je ne sais pas »)

- Modèle : openai/gpt-oss-120b (les modèles Llama de Groq ont été arrêtés le 16 août 2026), configurable via la variable GROQ_MODEL.
- Calibration du seuil sur 13 questions : dans le corpus 0.874 à 0.905, hors corpus 0.752 à 0.872.
- Seuil provisoire 0.85 : bloque 5 questions hors sujet sur 6 avant tout appel au LLM.
- La question sur les réseaux convolutifs (0.872) passe le seuil, mais le LLM refuse de répondre : le seuil seul ne suffit pas, d'où deux garde-fous (seuil de similarité + consigne du prompt).
- Sources : seuls les passages réellement cités ([1], [2]...) sont affichés. Température 0 pour des réponses reproductibles.
- Le prompt précise que les passages sont des données et non des instructions (protection contre l'injection de prompt).
- À mesurer au jour 4 : refus à tort (seuil trop haut) et réponses inventées (seuil trop bas).
## Jour 4 : évaluation

- Jeu de 20 questions (15 avec réponse, 5 sans réponse dans les documents), bonnes réponses relevées dans les PDF avec leur page. Notation automatique : éléments attendus dans la réponse + bonne source citée ; refus attendu pour les questions sans réponse.
- Le diagnostic distingue quatre types d'échec : recherche, refus à tort, réponse incorrecte, réponse inventée.

| Seuil | 20 questions (réglage) | 10 questions neuves |
|---|---|---|
| 0.85 | 18/20 | 8/10 |
| 0.84 | 19/20 | non mesuré |
| 0.82 | 20/20 | 9/10 |
| 0.80 | 20/20 | non mesuré |

- Les deux échecs à 0.85 étaient des refus à tort : scores 0.848 et 0.830, juste sous le seuil, alors que la bonne page était dans le top 4 (retrieval 15/15).
- Seuil retenu : 0.82. Attention : il a été choisi à partir des 20 questions, donc 20/20 est optimiste. Le chiffre non biaisé est celui des 10 questions neuves : 9/10, avec 5/5 refus corrects (aucune réponse inventée).
- Le second garde-fou fonctionne : les questions sur le salaire (0.825) et HTTP (0.821) passent le seuil, et le LLM les refuse.
- Échec restant (question 25, « fonctions d'activation dans le cours sur le perceptron ») : la page attendue n'est pas dans le top 8, mais les passages retrouvés, issus d'autres cours, traitent aussi des fonctions d'activation. Ma question était ambiguë. Limite connue : la recherche sémantique ne sait pas restreindre une question à un document.
- Piste d'amélioration : filtre sur la métadonnée « source » (Chroma `where`) ou détection du document visé dans la question.
- Limites de l'évaluation : petit échantillon (20 + 10 questions), notation par mots-clés (peut rejeter une réponse correcte formulée autrement), questions écrites par moi.
## Jour 5 : API FastAPI et agent à deux outils

- API : GET /health, POST /ask (RAG), POST /agent. Validation de la question (3 à 500 caractères), modèle et index chargés une seule fois au démarrage (lifespan), erreurs du LLM traduites en 429 et 502 sans détails internes.
- Agent : tool calling Groq avec deux outils, search_documents (même seuil de similarité que le RAG) et calculate (calculatrice sécurisée par analyse syntaxique, jamais d'eval). Plafond de 4 étapes.
- Essai réel : « notes 11, 13, 12, module validé en CI ? » -> recherche du seuil (12/20) puis calcul de la moyenne (12.0) -> validé. « 15 % de 300 heures » -> 45 h avec la source. Question hors sujet -> « Je ne sais pas » après un seul appel de recherche.
- Observation : l'agent a appelé la calculatrice avant la recherche dans un cas, malgré la consigne : l'ordre des outils est décidé par le LLM.
- Limites : l'agent n'est pas évalué sur un jeu de questions, il est plus coûteux (plusieurs appels au LLM) et moins reproductible que /ask. Les citations du LLM ne sont pas toujours mot pour mot, seules les sources (fichier et page) sont fiables.
## Jour 6 : Docker, docker-compose et CI

- Image Docker : python:3.13-slim, PyTorch version CPU (sans elle, pip installe une trentaine de paquets NVIDIA inutiles), modèle d'embedding téléchargé à la construction, exécution avec un utilisateur non administrateur. Taille : 4,18 Go sur disque, 1,16 Go compressés.
- Le port est lu dans la variable PORT (8080 par défaut), comme l'exige Cloud Run.
- docker-compose : monte le dossier data/ local (index privé, jamais copié dans l'image) et passe la clé API via .env.
- .dockerignore : exclut .env, data/, .git, tests et évaluation de l'image.
- Tests d'hygiène : .env ignoré par git et par Docker, aucune clé gsk_ dans les fichiers du dépôt. 35 tests au total.
- CI GitHub Actions : job tests (pytest, sans aucun secret car Groq est simulé) puis job docker (construction de l'image avec cache). Premier run vert en 5 min 34 s.
- Incident 1 : le build local a échoué sur un « TLS handshake timeout » vers Docker Hub. Cause : réseau interne de Docker Desktop, pas le Dockerfile (curl depuis Windows fonctionnait). Résolu en redémarrant Docker Desktop.
- Incident 2 : le fichier s'appelait « dockerfile » en minuscules. Sous Windows ça fonctionne, mais Linux (la CI) distingue la casse : renommé en « Dockerfile » avant le premier push.
- Limite : les dépendances principales sont fixées mais pas leurs dépendances secondaires (pas de verrouillage complet).