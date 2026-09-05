# ruff: noqa: E501
import numpy as np
import pandas as pd

from lfspanel.analysis import (
    demean,
    estimate_did,
    estimate_event_study,
    event_study_frame,
    quarter_index,
    wls_cluster,
)
from lfspanel.exposure import (
    _terciles,
    aggregate_isco,
    attach_exposure,
    occupation_scores,
)


def _tasks():
    rows = []
    for code, scores in {
        "1111": [0.2, 0.4],
        "1112": [0.6, 0.7],
        "2111": [0.1, 0.1],
        "2112": [0.5, 0.9],
    }.items():
        for i, s in enumerate(scores, 1):
            rows.append(
                {
                    "isco4": code,
                    "title": code,
                    "task_id": i,
                    "score_2023": s,
                    "score_2025": s,
                    "category": "Exposed: Gradient 4"
                    if np.mean(scores) >= 0.6
                    else "Not Exposed",
                }
            )
    return pd.DataFrame(rows)


def test_occupation_scores_and_aggregation():
    occ = occupation_scores(_tasks())
    assert (
        abs(occ.loc["1112", "score"] - 0.65) < 1e-9 and occ.loc["1112", "gradient"] == 4
    )
    assert occ.loc["1111", "high_task_share"] == 0.0
    weights = pd.Series({"1111": 100.0, "1112": 100.0, "2111": 300.0, "2112": 100.0})
    table = aggregate_isco(occ, weights)
    d2 = table[table["digits"] == 2].set_index("isco")
    assert abs(d2.loc["11", "score_w"] - 0.475) < 1e-9
    assert abs(d2.loc["21", "score_w"] - (0.1 * 300 + 0.7 * 100) / 400) < 1e-9
    assert d2.loc["21", "g4_share"] == 0.25
    assert set(table["digits"]) == {1, 2, 3, 4}


def test_terciles_weighted_by_employment():
    score = pd.Series({"a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4})
    weight = pd.Series({"a": 60.0, "b": 10.0, "c": 10.0, "d": 20.0})
    t = _terciles(score, weight)
    assert t["a"] == 2 and t["b"] == 3 and t["d"] == 3  # 'a' alone exceeds a third


def test_attach_exposure_by_digits():
    table = pd.DataFrame(
        {
            "digits": [2, 3],
            "isco": ["11", "111"],
            "score": [0.4, 0.5],
            "score_w": [0.4, 0.5],
            "g4_share": [0, 0],
            "tercile": [2, 3],
            "high": [0, 1],
        }
    )
    df = pd.DataFrame({"isco": ["11", "111"], "isco_digits": [2, 3]})
    out = attach_exposure(df, table)
    assert out["high"].tolist() == [0, 1]


def test_quarter_index():
    assert quarter_index("2022Q4") == 0
    assert quarter_index("2023Q1") == 1
    assert quarter_index("2022Q1") == -3


def _cells(seed=0):
    rng = np.random.default_rng(seed)
    periods = [f"{y}Q{q}" for y in (2022, 2023) for q in range(1, 5)]
    rows = []
    for isco in ["111", "112", "211", "212"]:
        high = isco.startswith("2")
        for age in ["15-21", "30-49"]:
            for male in (0, 1):
                for p in periods:
                    k = quarter_index(p)
                    effect = 0.2 * high * (k > 0)  # true post effect on log employment
                    emp = 1000 * np.exp(effect + 0.01 * rng.standard_normal())
                    rows.append(
                        {
                            "countrycode": "XXX",
                            "period": p,
                            "isco": isco,
                            "isco_digits": 3,
                            "age_group": age,
                            "male": male,
                            "n": 50,
                            "emp": emp,
                            "new_hire_share": 0.2,
                            "tenure_coverage": 1.0,
                            "formal_share": 0.5,
                            "employee_share": 0.6,
                            "young": int(age == "15-21"),
                            "small": 0,
                        }
                    )
    return pd.DataFrame(rows)


def _exposure():
    return pd.DataFrame(
        {
            "digits": 3,
            "isco": ["111", "112", "211", "212"],
            "score": [0.1, 0.2, 0.6, 0.7],
            "score_w": [0.1, 0.2, 0.6, 0.7],
            "g4_share": [0, 0, 1, 1],
            "tercile": [1, 1, 3, 3],
            "high": [0, 0, 1, 1],
        }
    )


def test_event_study_recovers_effect():
    frame = event_study_frame(_cells(), _exposure())
    assert len(frame) == 16 * 8 and frame["emp_base"].notna().all()
    es = estimate_event_study(frame)
    post = es[es["k"] > 0]["coef"]
    pre = es[es["k"] < 0]["coef"]
    assert abs(post.mean() - 0.2) < 0.02 and abs(pre.mean()) < 0.02
    did = estimate_did(frame, triple=True)
    assert abs(did.loc[did["term"] == "post_x_treat", "coef"].iloc[0] - 0.2) < 0.02
    assert abs(did.loc[did["term"] == "post_x_treat_x_young", "coef"].iloc[0]) < 0.02


def test_balanced_panel_fills_absent_cells():
    cells = _cells()
    cells = cells[~((cells["isco"] == "111") & (cells["period"] == "2023Q3"))]
    frame = event_study_frame(cells, _exposure())
    absent = frame[(frame["isco"] == "111") & (frame["period"] == "2023Q3")]
    assert (
        len(absent) == 4
        and (absent["emp"] == 0).all()
        and absent["log_emp"].isna().all()
    )
    assert (absent["emp_ratio"] == 0).all()


def test_demean_and_wls_cluster():
    df = pd.DataFrame(
        {
            "y": [1.0, 2.0, 3.0, 4.0],
            "g": ["a", "a", "b", "b"],
            "h": ["u", "v", "u", "v"],
        }
    )
    dm = demean(df, ["y"], ["g", "h"])
    assert np.allclose(dm["y"], 0.0, atol=1e-6)
    rng = np.random.default_rng(1)
    X = rng.standard_normal((200, 2))
    y = X @ np.array([1.0, -2.0]) + 0.1 * rng.standard_normal(200)
    beta, se = wls_cluster(y, X, np.ones(200), np.repeat(np.arange(20), 10))
    assert np.allclose(beta, [1.0, -2.0], atol=0.05) and (se > 0).all()
