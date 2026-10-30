FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TOKENIZERS_PARALLELISM=false \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

# 1) Dépendances : cette couche reste en cache tant que requirements.txt ne change pas.
#    L'index PyTorch CPU évite de télécharger la version GPU (plusieurs Go inutiles).
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# 2) Modèle d'embedding téléchargé à la construction : aucun téléchargement au démarrage.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
ENV HF_HUB_OFFLINE=1

# 3) Code seulement : l'image ne contient aucun document.
#    Les PDF sont montés dans /app/data/pdfs et indexés au premier démarrage (src/serve.py).
COPY src/ src/

# 4) Exécution avec un utilisateur non administrateur.
RUN useradd --create-home appuser \
    && mkdir -p data/pdfs data/processed data/chroma \
    && chown -R appuser /app /opt/hf-cache
USER appuser

EXPOSE 8080
CMD ["python", "-m", "src.serve"]