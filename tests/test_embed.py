import json

from src.embed import load_chunks


def test_load_chunks_reads_jsonl(tmp_path):
    f = tmp_path / "chunks.jsonl"
    rows = [{"id": "a_p1_c0", "text": "é"}, {"id": "a_p1_c1", "text": "b"}]
    f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    assert load_chunks(f) == rows