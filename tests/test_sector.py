import duckdb
import numpy as np
import pandas as pd

from lfspanel.analysis import estimate_did, quarter_index
from lfspanel.sector import (
    CONTROLS,
    _group_sql,
    build_sector_cells,
    sector_frame,
)


def _employed_view(con: duckdb.DuckDBPyConnection) -> None:
    """A tiny ``employed`` view: two countries, one quarter, four industries."""
    rows = []
    rid = 0
    for cc, codes in [
        ("BRA", ["6201", "6311", "8220", "6419", "6910", "8411", "0111"]),
        ("MEX", ["6419", "8411"]),
    ]:
        for code in codes:
            for male in (0, 1):
                for age in (20, 40):
                    rid += 1
                    rows.append(
                        dict(
                            countrycode=cc,
                            source="own",
                            period="2022Q1",
                            male=male,
                            age=age,
                            weight=10.0,
                            urban=1,
                            visit_no=1,
                            industrycat_isic=code,
                            industry_orig="5611"
                            if cc == "MEX" and code == "8411"
                            else "x",
                            occup_isco="4110" if age == 20 else "2511",
                        )
                    )
    df = pd.DataFrame(rows)
    con.register("emp_df", df)
    con.execute("CREATE VIEW employed AS SELECT * FROM emp_df")


def test_group_sql_country_exceptions():
    assert "'62', '63', '82'" in _group_sql("BRA")
    assert (
        "= '62'" in _group_sql("ZAF")
        and "'82'" not in _group_sql("ZAF").split("THEN 'itbpo'")[0]
    )
    assert "industry_orig = '5611'" in _group_sql("MEX")


def test_build_sector_cells():
    con = duckdb.connect()
    _employed_view(con)
    cells = build_sector_cells(con, countries=["BRA", "MEX"])
    bra = cells[cells["countrycode"] == "BRA"].set_index(["sector", "male"])
    assert set(cells["sector"]) == {"itbpo", "finance", "profserv", "pubadmin", "rest"}
    # 62, 63 and 82 pooled: three codes x two ages per sex
    assert bra.loc[("itbpo", 1), "n"] == 6 and bra.loc[("itbpo", 1), "emp"] == 60.0
    assert bra.loc[("itbpo", 1), "young_share"] == 0.5
    assert bra.loc[("itbpo", 1), "u25_share"] == 0.5
    assert bra.loc[("itbpo", 1), "cler_share"] == 0.5
    assert (
        bra.loc[("itbpo", 1), "cler_emp"] == 30.0
        and bra.loc[("itbpo", 1), "prof_emp"] == 30.0
    )
    assert (
        bra.loc[("itbpo", 1), "treated"] == 1
        and bra.loc[("finance", 0), "treated"] == 0
    )
    # Mexico: ENOE 5611 marks the treated group even though the ISIC code says 84
    mex = cells[cells["countrycode"] == "MEX"]
    assert set(mex["sector"]) == {"itbpo", "finance"}
    # agriculture (0111) lands in the rest-of-economy group
    assert bra.loc[("rest", 1), "n"] == 2
    # the default frame leaves the rest group out; it enters only when asked
    assert "rest" not in set(sector_frame(_sector_cells())["sector"])


def _sector_cells(effect=0.3, seed=0):
    rng = np.random.default_rng(seed)
    periods = [f"{y}Q{q}" for y in (2022, 2023) for q in range(1, 5)]
    rows = []
    for sector in ["itbpo"] + list(CONTROLS):
        for male in (0, 1):
            for p in periods:
                post = quarter_index(p) > 0
                treated = sector == "itbpo"
                emp = 1000 * np.exp(
                    effect * treated * post + 0.01 * rng.standard_normal()
                )
                share = 0.3 - 0.05 * treated * post + 0.001 * rng.standard_normal()
                rows.append(
                    dict(
                        countrycode="XXX",
                        period=p,
                        sector=sector,
                        male=male,
                        n=50,
                        emp=emp,
                        young_share=share,
                        u25_share=share,
                        cler_share=0.4,
                        cler_emp=0.4 * emp,
                        prof_emp=0.5 * emp,
                        treated=int(treated),
                        small=0,
                    )
                )
    return pd.DataFrame(rows)


def test_sector_frame_and_did():
    frame = sector_frame(_sector_cells())
    assert len(frame) == 8 * 8 and frame["emp_base"].notna().all()
    assert set(frame["cluster"]) == {f"XXX|{s}" for s in ["itbpo"] + list(CONTROLS)}
    assert frame["post"].sum() == 8 * 4
    did = estimate_did(frame, outcome="log_emp", treat="treated")
    assert abs(did["coef"].iloc[0] - 0.3) < 0.02
    did_share = estimate_did(frame, outcome="young_share", treat="treated")
    assert abs(did_share["coef"].iloc[0] + 0.05) < 0.005
    # restricting the controls drops the other groups
    fin = sector_frame(_sector_cells(), controls=("finance",))
    assert set(fin["sector"]) == {"itbpo", "finance"}
    # the baseline floor removes cells with too few observations
    small = _sector_cells()
    small.loc[small["sector"] == "pubadmin", "n"] = 10
    assert "pubadmin" not in set(sector_frame(small)["sector"])
