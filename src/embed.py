"""Jour 2 : embeddings multilingues et base vectorielle Chroma."""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
CHUNKS_FILE = Path("data/processed/chunks.jsonl")
CHROMA_DIR = "data/chroma"
COLLECTION = "eniad_docs"
BATCH_SIZE = 32


def load_chunks(path: Path = CHUNKS_FILE) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_passages(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    # Le modèle e5 attend le préfixe "passage: " pour les documents.
    return model.encode(
        [f"passage: {t}" for t in texts],
        normalize_embeddings=True,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
    ).tolist()


def embed_query(model: SentenceTransformer, question: str) -> list[float]:
    # ... et "query: " pour les questions.
    return model.encode(f"query: {question}", normalize_embeddings=True).tolist()


def get_collection(reset: bool = False):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass  # la collection n'existait pas encore
    return client.get_or_create_collection(
        COLLECTION, configuration={"hnsw": {"space": "cosine"}}
    )


def main() -> None:
    rows = load_chunks()
    model = load_model()
    collection = get_collection(reset=True)

    embeddings = embed_passages(model, [r["text"] for r in rows])
    collection.upsert(
        ids=[r["id"] for r in rows],
        embeddings=embeddings,
        documents=[r["text"] for r in rows],
        metadatas=[
            {"source": r["source"], "page": r["page"], "chunk_index": r["chunk_index"]}
            for r in rows
        ],
    )
    print(f"{collection.count()} chunks indexés dans {CHROMA_DIR}")


if __name__ == "__main__":
    main()