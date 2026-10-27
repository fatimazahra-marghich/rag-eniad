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

# 3) Code, puis index construit dans l'image seulement si corpus/ contient des PDF.
COPY src/ src/
COPY corpus/ data/pdfs/
RUN if ls data/pdfs/*.pdf >/dev/null 2>&1; then python src/ingest.py && python -m src.embed; fi

# 4) Exécution avec un utilisateur non administrateur.
RUN useradd --create-home appuser && chown -R appuser /app /opt/hf-cache
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8080}"]