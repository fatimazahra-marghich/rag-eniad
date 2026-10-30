import src.serve as serve


def test_needs_indexing_only_with_pdfs_and_empty_index():
    assert serve.needs_indexing(n_pdfs=3, index_size=0) is True
    assert serve.needs_indexing(n_pdfs=3, index_size=198) is False
    assert serve.needs_indexing(n_pdfs=0, index_size=0) is False


def run_main(monkeypatch, tmp_path, n_pdfs, size):
    (tmp_path / "data" / "pdfs").mkdir(parents=True)
    for i in range(n_pdfs):
        (tmp_path / "data" / "pdfs" / f"doc{i}.pdf").write_bytes(b"%PDF")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PORT", "9090")
    calls, started = [], {}
    monkeypatch.setattr(serve, "index_size", lambda: size)
    monkeypatch.setattr(serve.subprocess, "run", lambda cmd, check: calls.append(cmd))
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, host, port: started.update(app=app, port=port))
    serve.main()
    return calls, started


def test_main_indexes_then_serves_on_port_variable(monkeypatch, tmp_path):
    calls, started = run_main(monkeypatch, tmp_path, n_pdfs=2, size=0)
    assert len(calls) == 2 and started == {"app": "src.api:app", "port": 9090}


def test_main_skips_indexing_when_index_exists(monkeypatch, tmp_path):
    calls, started = run_main(monkeypatch, tmp_path, n_pdfs=2, size=198)
    assert calls == [] and started["port"] == 9090