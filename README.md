# Assistant RAG en français (ENIAD)

![CI](https://github.com/fatimazahra-marghich/rag-eniad/actions/workflows/ci.yml/badge.svg)

Application qui répond à des questions en français sur un ensemble de documents (règlement de l'ENIAD, cours d'Agile et de Deep Learning). Chaque réponse indique ses sources (fichier et page), et l'assistant répond « Je ne sais pas » quand l'information n'est pas dans les documents.

Projet personnel: RAG, embeddings multilingues, base vectorielle, API FastAPI, agent avec tool calling, conteneurisation Docker et intégration continue.

**État :** ingestion, recherche, génération, évaluation, API, agent, tests (38), CI GitHub Actions et image Docker publique terminés. L'application se lance en une commande avec Docker, avec tes propres PDF.

## Démonstration

Captures de l'API (Swagger, `/docs`) :

**Question sur le règlement : réponse avec sources (fichier et page)**

![Question sur le règlement](docs/img/ask-reglement.png)

**Question de cours**

![Question de cours](docs/img/ask-cours.png)

**Question hors sujet : refus (`answered: false`, aucune source, score 0.752 sous le seuil 0.82)**

![Refus sur une question hors sujet](docs/img/ask-inconnu.png)

**Agent : appel de l'outil calculatrice**

![Agent avec calcul](docs/img/agent-calcul.png)

## Fonctionnement

```mermaid
flowchart LR
    A[PDF] --> B[Extraction PyMuPDF<br/>nettoyage + chunks]
    B --> C[Embeddings<br/>multilingual-e5-small]
    C --> D[(Chroma)]
    Q[Question] --> E[Embedding de la question]
    E --> D
    D --> F{Score >= seuil 0.82 ?}
    F -- non --> G[Je ne sais pas]
    F -- oui --> H[LLM Groq<br/>gpt-oss-120b]
    H --> I[Réponse + sources]
```

Deux garde-fous contre les réponses inventées : un seuil de similarité (aucun appel au LLM si aucun passage n'est assez proche) et une consigne au LLM de refuser si les passages ne contiennent pas la réponse.

## Résultats d'évaluation

Évaluation automatique : 15 questions avec réponse (éléments attendus + bonne source citée) et 5 questions sans réponse dans les documents (refus attendu).

| Mesure | Résultat |
|---|---|
| Seuil de départ (0.85), 20 questions | 18/20 |
| Seuil retenu (0.82), 20 questions de réglage | 20/20 |
| Seuil retenu (0.82), 10 questions neuves jamais utilisées pour le réglage | 9/10 |
| Refus corrects sur les questions sans réponse (30 questions) | 10/10 |

Le seuil de 0.82 a été choisi à partir des 20 premières questions : le 20/20 est donc optimiste. Le chiffre le plus fiable est **9/10 sur les questions neuves**. Détails et diagnostics par question : [`evaluation/results.md`](evaluation/results.md), et comparaison des seuils dans `evaluation/results_seuil_*.md`.

Limites de l'évaluation : petit échantillon, questions écrites par moi, notation par mots-clés (peut rejeter une réponse correcte formulée autrement). L'agent n'est pas évalué.

## API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | État du service, taille de l'index |
| POST | `/ask` | Question -> réponse, sources, score |
| POST | `/agent` | Agent à deux outils (recherche dans les documents, calculatrice) |

Documentation interactive : `http://localhost:8000/docs`.

## Lancer avec Docker (recommandé)

L'image est publiée automatiquement par la CI sur GitHub Container Registry. **Elle ne contient aucun document** : tu montes tes propres PDF (avec texte sélectionnable), et l'index est construit au premier démarrage.

Prérequis : Docker, une clé API gratuite [Groq](https://console.groq.com/keys).

```powershell
# 1. Fichier de configuration (puis renseigner GROQ_API_KEY)
Copy-Item .env.example .env

# 2. Dossier de documents : mets tes PDF dans data/pdfs/
mkdir data\pdfs

# 3. Télécharger et lancer l'image
docker pull ghcr.io/fatimazahra-marghich/rag-eniad:latest
docker run --rm -p 8000:8080 --env-file .env -v "${PWD}/data:/app/data" ghcr.io/fatimazahra-marghich/rag-eniad:latest
```

Sous Linux ou macOS, remplace `"${PWD}/data"` par `"$(pwd)/data"`.

- Au premier démarrage, les PDF sont indexés (quelques minutes selon le nombre de pages). L'index est conservé dans `data/chroma/` : les démarrages suivants sont immédiats.
- Sans PDF, l'API démarre mais répond « Je ne sais pas » à tout, et un avertissement s'affiche dans les logs.
- Ouvre ensuite `http://localhost:8000/docs`. Pour réindexer après un changement de PDF, supprime `data/chroma/`.

Avec docker-compose (construit l'image localement) : `docker compose up --build`.

## Lancer en local (sans Docker)

Prérequis : Python 3.11 ou plus, une clé API Groq.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # puis renseigner GROQ_API_KEY
```

Les documents ne sont pas publiés dans ce dépôt (règlement et cours : droits de diffusion). Place tes PDF dans `data/pdfs/`, puis :

```powershell
python src/ingest.py               # extraction et chunks
python -m src.embed                # embeddings et index Chroma
uvicorn src.api:app --port 8000    # API
pytest -v                          # tests
python -m src.evaluate             # évaluation (nécessite questions.json adapté à tes documents)
```

## Choix techniques

- **PyMuPDF** plutôt que pypdf : pypdf collait des mots (« Réseauxde ») sur mes PDF.
- **multilingual-e5-small** : multilingue, contexte de 512 tokens, léger. `paraphrase-multilingual-MiniLM` tronque à 128 tokens ; `bge-m3` est trop lourd pour un niveau gratuit.
- **Chroma** : base embarquée sans serveur, suffisante pour quelques centaines de passages.
- **Calculatrice de l'agent** : analyse syntaxique avec liste blanche d'opérateurs, jamais `eval` sur du texte venant du LLM.
- **Modèle LLM configurable** (`GROQ_MODEL`) : les modèles Llama que j'utilisais sur Groq ont été arrêtés en août 2026.
- **Docker** : PyTorch en version CPU (plusieurs Go de moins), modèle d'embedding téléchargé à la construction (aucun téléchargement au démarrage), utilisateur non administrateur, couches ordonnées pour profiter du cache.
- **Image sans documents** : l'index est construit au démarrage à partir des PDF montés. Rien de privé ne se retrouve dans une image publique.
- **CI** (GitHub Actions) : tests à chaque push, construction de l'image, publication sur GHCR depuis `main`.

## Limites connues

- **Les sources indiquent le fichier et la page.** Les citations reformulées par le LLM ne sont pas garanties exactes au caractère près : elles servent à retrouver le passage, pas à le recopier.
- Les tableaux des PDF sont aplatis, les schémas et formules en image ne sont pas extraits, pas d'OCR.
- La recherche sémantique ne sait pas restreindre une question à un document précis (piste : filtre sur la métadonnée `source`). Sur le jeu de questions neuves, la question Q25 échoue pour cette raison (question ambiguë, conservée telle quelle).
- Corpus de 6 documents : les résultats ne se généralisent pas à un autre corpus.
- Pas de démo en ligne : l'application se lance soi-même avec Docker.

## Structure

```
src/          ingest.py, embed.py, search.py, rag.py, evaluate.py, agent.py, api.py, serve.py
tests/        tests unitaires (aucun appel réseau)
evaluation/   questions, résultats et comparaisons de seuils
docs/img/     captures de l'API
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
NOTES.md      journal de développement et décisions
```