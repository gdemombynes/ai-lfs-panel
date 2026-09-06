from lfspanel.fetch.zaf import CATALOG_IDS, catalog_url, fetch_period, find_zip
from lfspanel.periods import Period


def test_catalog_url_and_missing_period():
    assert catalog_url(Period("2026Q2")).endswith("/catalog/1247/get-microdata")
    assert len(CATALOG_IDS) == 18
    try:
        catalog_url(Period("2030Q1"))
    except FileNotFoundError as exc:
        assert "2030Q1" in str(exc)


def test_fetch_period_reports_manual_when_absent(monkeypatch, tmp_path):
    import lfspanel.fetch.zaf as zaf

    monkeypatch.setattr(zaf, "period_dir", lambda p: tmp_path / str(p))
    res = fetch_period(Period("2025Q1"))
    assert (
        res[0].status == "failed"
        and "MANUAL" in res[0].error
        and "1026" in res[0].error
    )
    (tmp_path / "2025Q1").mkdir()
    (tmp_path / "2025Q1" / "qlfs-2025-q1-v1-stata.zip").write_bytes(b"PK")
    assert find_zip(Period("2025Q1")).name == "qlfs-2025-q1-v1-stata.zip"
