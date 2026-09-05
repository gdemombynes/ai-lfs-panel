import pandas as pd

from lfspanel.validate import (
    compare_official,
    employment_by_major_group,
    headline_rates,
)


def test_headline_rates(harmonized_frame):
    r = headline_rates(harmonized_frame)
    # population 14+: weights 100+80+120+60 = 360; LF = 240;
    # employed = 160; unemployed = 80
    assert round(r["participation_rate"], 4) == round(100 * 240 / 360, 4)
    assert round(r["unemployment_rate"], 4) == round(100 * 80 / 240, 4)
    assert round(r["employment_rate"], 4) == round(100 * 160 / 360, 4)


def test_compare_official_pass_fail(harmonized_frame):
    rates = headline_rates(harmonized_frame)
    official = pd.DataFrame(
        {
            "period": ["2025Q1", "2025Q1"],
            "indicator": ["unemployment_rate", "participation_rate"],
            "value": [33.3, 60.0],
            "tolerance": [0.2, 0.2],
            "source_url": ["", ""],
        }
    )
    out = compare_official(rates, official, "2025Q1")
    assert list(out["status"]) == ["PASS", "FAIL"]


def test_employment_by_major_group(harmonized_frame):
    shares = employment_by_major_group(harmonized_frame)
    assert round(float(shares.loc[2]), 2) == 62.5
