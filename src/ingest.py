"""Jour 1 : extraction des PDF et découpage en chunks avec métadonnées."""
import json
import re
import statistics
from collections import Counter
from pathlib import Path

import pymupdf

CHUNK_SIZE = 800   # caractères max par chunk (≈ 150-200 mots)
OVERLAP = 150      # caractères repris du chunk précédent
MIN_CHARS = 80     # on jette les chunks trop courts (titres seuls, numéros...)
REPEAT_RATIO = 0.4  # une ligne présente sur 40 % des pages = en-tête/pied de page

PAGE_NUM_RE = re.compile(r"^\s*\d+\s*(/\s*\d+)?\s*$")  # "4" ou "42/ 53"


def strip_boilerplate(pages: list[str]) -> list[str]:
    """Supprime numéros de page et lignes répétées (en-têtes, pieds de page)."""
    counts: Counter = Counter()
    for page in pages:
        lines = {re.sub(r"\d+", "#", ln.strip()) for ln in page.splitlines() if ln.strip()}
        counts.update(lines)

    threshold = max(3, int(REPEAT_RATIO * len(pages)))
    cleaned_pages = []
    for page in pages:
        kept = []
        for ln in page.splitlines():
            norm = re.sub(r"\d+", "#", ln.strip())
            if PAGE_NUM_RE.match(ln):
                continue
            if len(norm) >= 15 and counts[norm] >= threshold:
                continue
            kept.append(ln)
        cleaned_pages.append("\n".join(kept))
    return cleaned_pages


def clean(text: str) -> str:
    """Nettoie le texte brut sorti du PDF."""
    text = text.replace("\u00ad", "")                  # trait d'union conditionnel
    text = re.sub(r"[.…]{4,}", " ", text)              # points de suite (formulaires)
    text = re.sub(r"-\n(\w)", r"\1", text)             # mot coupé en fin de ligne
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)       # saut de ligne simple -> espace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n\n", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Regroupe des phrases entières jusqu'à `size` caractères, avec chevauchement."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for sentence in split_sentences(text):
        # phrase plus longue que la taille max : découpe forcée
        while len(sentence) > size:
            if current:
                chunks.append(" ".join(current))
                current, length = [], 0
            chunks.append(sentence[:size])
            sentence = sentence[size - overlap:]

        if current and length + len(sentence) + 1 > size:
            chunks.append(" ".join(current))
            # on garde les dernières phrases comme chevauchement
            tail: list[str] = []
            tail_len = 0
            for prev in reversed(current):
                if tail_len + len(prev) > overlap:
                    break
                tail.insert(0, prev)
                tail_len += len(prev) + 1
            current, length = tail, tail_len

        current.append(sentence)
        length += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))
    return chunks


def process_pdf(path: Path) -> tuple[list[dict], int, int]:
    """Retourne (chunks, nb_pages, nb_pages_vides)."""
    with pymupdf.open(path) as doc:
        raw_pages = [page.get_text() for page in doc]
    pages = strip_boilerplate(raw_pages)

    records: list[dict] = []
    empty_pages = 0
    for page_num, raw in enumerate(pages, start=1):
        text = clean(raw)
        if not text:
            empty_pages += 1
            continue
        for i, chunk in enumerate(chunk_text(text)):
            if len(chunk) < MIN_CHARS:
                continue
            records.append({
                "id": f"{path.stem}_p{page_num}_c{i}",
                "text": chunk,
                "source": path.name,
                "page": page_num,
                "chunk_index": i,
                "n_chars": len(chunk),
            })
    return records, len(pages), empty_pages


def main() -> None:
    pdf_dir = Path("data/pdfs")
    out_file = Path("data/processed/chunks.jsonl")
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("Aucun PDF dans data/pdfs/")

    all_records: list[dict] = []
    for pdf in pdfs:
        records, n_pages, n_empty = process_pdf(pdf)
        print(f"{pdf.name}: {n_pages} pages, {n_empty} vides, {len(records)} chunks")
        if n_empty > n_pages * 0.3:
            print("  ATTENTION : beaucoup de pages vides, PDF scanné ? (OCR nécessaire)")
        all_records.extend(records)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    sizes = [r["n_chars"] for r in all_records]
    print(f"\nTotal : {len(all_records)} chunks -> {out_file}")
    print(f"Taille (caractères) : min={min(sizes)}, "
          f"médiane={int(statistics.median(sizes))}, max={max(sizes)}")


if __name__ == "__main__":
    main()