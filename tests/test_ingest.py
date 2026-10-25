from src.ingest import clean, chunk_text, strip_boilerplate

def test_clean_joins_hyphenated_words():
    assert clean("le règle-\nment intérieur") == "le règlement intérieur"


def test_short_text_gives_one_chunk():
    assert chunk_text("Une phrase courte.") == ["Une phrase courte."]


def test_chunks_respect_max_size():
    text = " ".join(f"Phrase numéro {i} du règlement." for i in range(200))
    chunks = chunk_text(text, size=300, overlap=60)
    assert len(chunks) > 1
    assert all(len(c) <= 300 + 60 for c in chunks)   # marge due au chevauchement


def test_overlap_between_consecutive_chunks():
    text = " ".join(f"Phrase numéro {i} du règlement." for i in range(200))
    chunks = chunk_text(text, size=300, overlap=60)
    last_sentence = chunks[0].split(". ")[-1]
    assert last_sentence in chunks[1]
    
def test_strip_boilerplate_removes_header_and_page_numbers():
    contents = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    pages = [f"ENTETE ECOLE ENIAD Page {i} sur 6\n{word} propre\n{i}"
             for i, word in enumerate(contents, start=1)]
    result = strip_boilerplate(pages)
    assert all("ENTETE" not in p for p in result)
    assert result[0].strip() == "alpha propre"


def test_clean_removes_dot_leaders():
    assert clean("Nom : ………………………… Signature") == "Nom : Signature"