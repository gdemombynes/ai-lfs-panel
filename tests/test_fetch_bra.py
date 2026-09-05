from lfspanel.fetch.bra import candidate_names, release_date
from lfspanel.periods import Period

LISTING = """
<a href="PNADC_012024_20250815.zip">PNADC_012024_20250815.zip</a>
<a href="PNADC_022024_20250815.zip">PNADC_022024_20250815.zip</a>
<a href="PNADC_022024_20260324.zip">PNADC_022024_20260324.zip</a>
<a href="PNADC_032024_20250815.zip">PNADC_032024_20250815.zip</a>
"""


def test_candidate_names_picks_newest_release():
    assert candidate_names(LISTING, Period("2024Q2")) == [
        "PNADC_022024_20250815.zip",
        "PNADC_022024_20260324.zip",
    ]
    assert candidate_names(LISTING, Period("2024Q4")) == []
    assert candidate_names('href="PNADC_012025.zip"', Period("2025Q1")) == [
        "PNADC_012025.zip"
    ]


def test_release_date():
    assert release_date("PNADC_022024_20260324.zip") == "2026-03-24"
    assert release_date("PNADC_012025.zip") is None
    assert (
        release_date("data/raw/bra/pnadc/2022Q1/PNADC_012022_20250815.zip")
        == "2025-08-15"
    )
