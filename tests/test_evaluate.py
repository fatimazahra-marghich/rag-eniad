from src.evaluate import matches_all, normalize, source_ok


def test_normalize_removes_accents_and_curly_quotes():
    assert normalize("Plus d’une SÉANCE") == "plus d'une seance"


def test_matches_all_requires_every_item():
    assert matches_all("Entre 6 et 10 membres", ["6", "10"])
    assert not matches_all("Entre 6 membres", ["6", "10"])


def test_matches_all_accepts_alternatives():
    assert matches_all("C'est interdit.", ["interdit|interdiction"])
    assert matches_all("Il faut cinq absences", ["cinq|5"])


def test_source_ok_checks_file_and_page():
    sources = [{"source": "a.pdf", "page": 2, "score": 0.9}]
    assert source_ok(sources, "a.pdf", [1, 2])
    assert not source_ok(sources, "a.pdf", [3])
    assert not source_ok(sources, "b.pdf", [2])