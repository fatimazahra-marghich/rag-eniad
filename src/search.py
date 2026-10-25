"""Jour 2 : recherche des passages les plus proches d'une question."""
import sys

from src.embed import embed_query, get_collection, load_model


def search(question: str, k: int = 3, model=None, collection=None) -> list[dict]:
    model = model or load_model()
    collection = collection or get_collection()
    res = collection.query(
        query_embeddings=[embed_query(model, question)],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(1 - dist, 3),   # distance cosinus -> similarité
        }
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    model, collection = load_model(), get_collection()
    for question in sys.argv[1:]:
        print(f"\n### {question}")
        for hit in search(question, model=model, collection=collection):
            print(f"  [{hit['score']:.3f}] {hit['source']} p.{hit['page']} : "
                  f"{hit['text'][:140]}...")


if __name__ == "__main__":
    main()
    