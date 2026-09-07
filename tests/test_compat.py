import pandas as pd

from lfspanel.compat import (
    ISIC_DIVISIONS,
    _invalid_code_shares,
    coverage_table,
    flag_profile,
    missing_quarters,
)


def _profile():
    rows = []
    for i, p in enumerate(["2022Q1", "2022Q2", "2022Q3", "2022Q4", "2023Q1"]):
        rows.append(
            {
                "countrycode": "AAA",
                "period": p,
                "minlaborage": 15,
                "raw_release": "r1",
                "n_rows": 1000 if i < 3 else 2000,
                "pop": 100.0,
                "pop15_share": 70.0,
                "lfpr": 60.0 + (5 if p == "2023Q1" else 0),
                "ur": 5.0,
                "urban_pct": 50.0,
                "male_pct": 50.0,
                "miss_lstatus_pct": 0.0,
                "miss_occup_pct": 8.0 if i == 4 else 1.0,
                "miss_isic_pct": 0.0,
                "invalid_isco_pct": 0.0,
                "invalid_isic_pct": 0.0,
                "occup_mismatch_pct": 0.0,
                "dup_pid": 0,
                "bad_weight": 0,
                "bad_age": 0,
                "status_below_min": 0,
                "month_outside_pct": 0.0,
                "isco3_pct": 90.0,
                "isco4_pct": 80.0,
                "isic3_pct": 50.0,
                "miss_tenure_pct": 100.0,
                "miss_wage_pct": 20.0,
                "miss_educat7_pct": 0.0,
                "miss_empstat_pct": 0.0,
                "miss_whours_pct": 0.0,
                "miss_socialsec_pct": 0.0,
                "miss_contract_pct": 0.0,
                "employee_pct": 50.0,
                "agri_pct": 10.0,
            }  # fmt: skip
        )
    return pd.DataFrame(rows)


def test_flag_profile_levels_and_jumps():
    flags = flag_profile(_profile())
    kinds = set(zip(flags["kind"], flags["metric"], flags["period"]))
    assert ("level", "miss_occup_pct", "2023Q1") in kinds
    assert ("jump", "n_rows", "2022Q4") in kinds  # 1000 -> 2000 rows
    assert ("jump", "lfpr", "2023Q1") in kinds
    assert not any(k == "jump" and p == "2022Q1" for k, _, p in kinds)


def test_missing_quarters_and_coverage():
    assert missing_quarters(["2022Q1", "2022Q3", "2023Q1"]) == ["2022Q2", "2022Q4"]
    assert missing_quarters([]) == []
    cov = coverage_table(_profile())
    assert cov.loc[0, "first"] == "2022Q1" and cov.loc[0, "last"] == "2023Q1"
    assert cov.loc[0, "gaps"] == "" and cov.loc[0, "quarters"] == 5
    assert cov.loc[0, "tenure_pct"] == 0.0 and not cov.loc[0, "urban_only"]


def test_invalid_code_shares():
    codes = pd.DataFrame(
        {
            "countrycode": ["AAA"] * 4,
            "period": ["2022Q1"] * 4,
            "occup_isco": ["2110", "9999", "4222", None],
            "d": [3, 4, 4, None],
            "div": ["62", "34", "82", None],
            "w": [1.0, 1.0, 1.0, 1.0],
        }
    )
    out = _invalid_code_shares(codes)
    assert "34" not in ISIC_DIVISIONS and "62" in ISIC_DIVISIONS
    assert out.loc[0, "invalid_isco_pct"] == 25.0
    assert out.loc[0, "invalid_isic_pct"] == 25.0
