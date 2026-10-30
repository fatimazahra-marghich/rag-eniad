"""Point d'entrée du conteneur : indexe les PDF montés si besoin, puis lance l'API."""
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from src.embed import get_collection

PDF_DIR = Path("data/pdfs")


def needs_indexing(n_pdfs: int, index_size: int) -> bool:
    """Indexer seulement s'il y a des PDF et que l'index est vide."""
    return n_pdfs > 0 and index_size == 0


def index_size() -> int:
    return get_collection().count()


def main() -> None:
    n_pdfs = len(list(PDF_DIR.glob("*.pdf")))
    size = index_size()
    if needs_indexing(n_pdfs, size):
        print(f"Index vide : indexation de {n_pdfs} PDF depuis {PDF_DIR}...", flush=True)
        subprocess.run([sys.executable, "src/ingest.py"], check=True)
        subprocess.run([sys.executable, "-m", "src.embed"], check=True)
    elif n_pdfs == 0 and size == 0:
        print("ATTENTION : aucun document. Monte un dossier contenant "
              "pdfs/*.pdf sur /app/data (voir le README).", flush=True)
    uvicorn.run("src.api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


if __name__ == "__main__":
    main()