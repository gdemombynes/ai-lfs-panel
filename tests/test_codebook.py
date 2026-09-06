# ruff: noqa: E501
import json

import pandas as pd
import pytest

from lfspanel import codebook
from lfspanel.periods import Period


@pytest.fixture
def tmp_codebooks(tmp_path, monkeypatch):
    monkeypatch.setattr(codebook, "CODEBOOKS", tmp_path)
    return tmp_path


def _raw(status_codes, extra=None, n=200):
    df = pd.DataFrame(
        {
            "ANO4": ["2025"] * n,
            "CODUSU": [f"h{i}" for i in range(n)],
            "STATUS": [status_codes[i % len(status_codes)] for i in range(n)],
            "AGE": [str(15 + i % 60) for i in range(n)],
            "source_file": ["x.zip:x.txt"] * n,
        }
    )
    if extra is not None:
        df["CAT"] = extra
    return df


def test_fingerprint_classifies_variables(tmp_codebooks):
    path = codebook.fingerprint(
        _raw(["1", "2", "3"], extra=["a"] * 200), "xxx", Period("2025Q1")
    )
    doc = json.loads(path.read_text())
    assert set(doc["variables"]) == {"STATUS", "AGE", "CAT"}  # ids and year ignored
    assert doc["variables"]["STATUS"]["kind"] == "codes"
    assert doc["variables"]["STATUS"]["codes"] == {"1": 67, "2": 67, "3": 66}
    assert doc["variables"]["AGE"]["kind"] == "continuous"
    assert doc["variables"]["AGE"]["min"] == 15


def test_diff_codebooks_flags_new_and_removed_codes(tmp_codebooks):
    codebook.fingerprint(
        _raw(["1", "2", "3"], extra=["a"] * 200), "xxx", Period("2025Q1")
    )
    codebook.fingerprint(_raw(["1", "2", "4"]), "xxx", Period("2025Q2"))
    d = codebook.diff_codebooks("xxx")
    changes = set(zip(d["variable"], d["change"]))
    assert ("CAT", "variable_removed") in changes
    assert ("STATUS", "codes_added") in changes and (
        "STATUS",
        "codes_removed",
    ) in changes
    added = d[(d["variable"] == "STATUS") & (d["change"] == "codes_added")].iloc[0]
    assert added["detail"] == "4" and abs(added["share"] - 66 / 200) < 1e-6
    strict = codebook.diff_codebooks("xxx", min_share=0.5)
    assert set(strict["change"]) == {
        "variable_removed"
    }  # code changes below the floor drop


def test_distribution_drift_flags_level_shift():
    import duckdb

    rows = []
    for q, share in [("2024Q1", 30), ("2024Q2", 30), ("2024Q3", 40), ("2024Q4", 40)]:
        rows += [("XXX", q, 1, 1, 1, share)] + [("XXX", q, 1, 2, 1, 100 - share)]
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE harmonized(countrycode VARCHAR, period VARCHAR, lstatus INT, occup INT, "
        "urban INT, weight DOUBLE)"
    )
    con.executemany("INSERT INTO harmonized VALUES (?,?,?,?,?,?)", rows)
    con.execute("CREATE VIEW employed AS SELECT * FROM harmonized WHERE lstatus = 1")
    d = codebook.distribution_drift(con, variables=["occup"])
    flagged = d[d["flag"] != ""]
    assert set(flagged["period"]) == {"2024Q3"} and set(flagged["flag"]) == {
        "level_shift"
    }
