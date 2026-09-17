# ruff: noqa: E501
"""Philippines: recent tabulations of IT and business-process employment.

Combines three series to extend the sector picture past the public-use
files: PSA OpenSTAT monthly employment by industry section (J information
and communication, N administrative and support services, which holds call
centres) through the latest month; the same sections and the ISIC 62+63+82
block from the harmonised LFS, quarterly; and IBPAP's annual full-time
headcount for the IT-BPM industry. Everything indexed to 2022 = 100.

Writes output/tables/phl_sector_leading.csv and
output/figures/phl_sector_leading.png.
"""

from __future__ import annotations

import json
import subprocess

import duckdb
import matplotlib
import pandas as pd

from lfspanel.config import OUTPUT, PROCESSED

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TABLE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1B/LFS/0101B3FEMP2.px"
SECTIONS = {"0": "total", "14": "J_info_comm", "18": "N_admin_support"}
YEARS = {"9": 2021, "10": 2022, "11": 2023, "12": 2024, "13": 2025, "14": 2026}
# IBPAP full-time employees, end of year, millions (industry roadmap updates
# and year-end statements; 2025 from the January 2026 statement; 2026 forecast)
IBPAP = {2021: 1.44, 2022: 1.57, 2023: 1.70, 2024: 1.82, 2025: 1.90}
IBPAP_FORECAST = {2026: 1.96, 2027: 1.99}


def fetch_openstat() -> pd.DataFrame:
    query = {
        "query": [
            {"code": "Year", "selection": {"filter": "item", "values": list(YEARS)}},
            {
                "code": "Month",
                "selection": {"filter": "item", "values": [str(i) for i in range(12)]},
            },
            {
                "code": "Major Industry Group (2009 PSIC Code)",
                "selection": {"filter": "item", "values": list(SECTIONS)},
            },
        ],
        "response": {"format": "json"},
    }
    proc = subprocess.run(
        [
            "curl",
            "-sS",
            "-L",
            "-m",
            "120",
            "-A",
            "Mozilla/5.0 (Macintosh)",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(query),
            TABLE,
        ],
        capture_output=True,
        text=True,
        timeout=150,
        check=True,
    )
    data = json.loads(proc.stdout.lstrip("﻿"))
    rows = []
    for r in data["data"]:
        y, m, s = r["key"]
        v = r["values"][0]
        if v in (".", "..", ""):
            continue
        rows.append(
            {
                "year": YEARS[y],
                "month": int(m) + 1,
                "series": SECTIONS[s],
                "thousands": float(v),
            }
        )
    df = pd.DataFrame(rows)
    df["period"] = (
        df["year"].astype(str) + "Q" + ((df["month"] - 1) // 3 + 1).astype(str)
    )
    return df


def panel_series() -> pd.DataFrame:
    con = duckdb.connect(str(PROCESSED / "panel.duckdb"), read_only=True)
    df = con.execute("""
        select period,
          sum(weight)/1e3 total,
          sum(case when substr(industrycat_isic,1,2) between '58' and '63' then weight end)/1e3 J_info_comm,
          sum(case when substr(industrycat_isic,1,2) between '77' and '82' then weight end)/1e3 N_admin_support,
          sum(case when substr(industrycat_isic,1,2) in ('62','63','82') then weight end)/1e3 itbpo,
          sum(case when substr(industrycat_isic,1,2) in ('62','63','82') and age < 25 then weight end)
            / sum(case when substr(industrycat_isic,1,2) in ('62','63','82') then weight end) * 100 itbpo_u25,
          count(case when substr(industrycat_isic,1,2) in ('62','63','82') then 1 end) n_itbpo
        from employed where source='own' and countrycode='PHL' group by 1 order by 1""").df()
    con.close()
    return df


def main() -> None:
    ps = fetch_openstat()
    monthly = ps.pivot_table(
        index=["year", "month", "period"], columns="series", values="thousands"
    ).reset_index()
    base = monthly[monthly["year"] == 2022][
        ["total", "J_info_comm", "N_admin_support"]
    ].mean()
    for c in base.index:
        monthly[c + "_idx"] = 100 * monthly[c] / base[c]
    lfs = panel_series()
    lbase = lfs[lfs["period"].str.startswith("2022")][
        ["total", "J_info_comm", "N_admin_support", "itbpo"]
    ].mean()
    for c in lbase.index:
        lfs[c + "_idx"] = 100 * lfs[c] / lbase[c]
    ib = pd.DataFrame(
        {
            "year": list(IBPAP) + list(IBPAP_FORECAST),
            "millions": list(IBPAP.values()) + list(IBPAP_FORECAST.values()),
            "forecast": [False] * len(IBPAP) + [True] * len(IBPAP_FORECAST),
        }
    )
    ib["idx"] = 100 * ib["millions"] / IBPAP[2022]

    tables = OUTPUT / "tables"
    out = pd.concat(
        [
            monthly.assign(source="PSA OpenSTAT monthly")[
                [
                    "source",
                    "year",
                    "month",
                    "period",
                    "total",
                    "J_info_comm",
                    "N_admin_support",
                    "total_idx",
                    "J_info_comm_idx",
                    "N_admin_support_idx",
                ]
            ],
            lfs.assign(source="harmonised LFS quarterly"),
            ib.assign(source="IBPAP annual headcount"),
        ],
        ignore_index=True,
    )
    out.round(2).to_csv(tables / "phl_sector_leading.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    ax = axes[0]
    t = monthly.copy()
    t["x"] = t["year"] + (t["month"] - 1) / 12
    ax.plot(
        t["x"],
        t["N_admin_support_idx"],
        color="#dd8452",
        lw=1,
        label="PSA monthly: section N admin. and support",
    )
    ax.plot(
        t["x"],
        t["J_info_comm_idx"],
        color="#4c72b0",
        lw=1,
        label="PSA monthly: section J information and communication",
    )
    ax.plot(
        t["x"], t["total_idx"], color="grey", lw=1, label="PSA monthly: all employment"
    )
    q = lfs.copy()
    q["x"] = (
        q["period"].str[:4].astype(int)
        + (q["period"].str[-1].astype(int) - 1) / 4
        + 0.125
    )
    ax.plot(
        q["x"],
        q["N_admin_support_idx"],
        "s",
        color="#dd8452",
        ms=4,
        label="harmonised LFS: section N",
    )
    ax.plot(
        q["x"],
        q["J_info_comm_idx"],
        "s",
        color="#4c72b0",
        ms=4,
        label="harmonised LFS: section J",
    )
    ax.axhline(100, color="grey", lw=0.6)
    ax.axvline(2022.75, color="grey", ls="--", lw=0.8)
    ax.set_title("Industry sections, PSA monthly vs harmonised quarterly", fontsize=9)
    ax.set_ylabel("2022 = 100")
    ax.legend(fontsize=6.5)
    ax = axes[1]
    ax.plot(
        q["x"],
        q["itbpo_idx"],
        "o-",
        ms=3,
        label="harmonised LFS: ISIC 62+63+82, quarterly",
    )
    ax.plot(
        ib.loc[~ib.forecast, "year"] + 0.5,
        ib.loc[~ib.forecast, "idx"],
        "D-",
        color="#c44e52",
        ms=5,
        label="IBPAP full-time headcount, end-year",
    )
    ax.plot(
        ib.loc[ib.forecast, "year"] + 0.5,
        ib.loc[ib.forecast, "idx"],
        "D--",
        color="#c44e52",
        ms=5,
        mfc="white",
        label="IBPAP forecast (2026, 2027)",
    )
    ax.plot(t["x"], t["total_idx"], color="grey", lw=1, label="all employment (PSA)")
    ax.axhline(100, color="grey", lw=0.6)
    ax.axvline(2022.75, color="grey", ls="--", lw=0.8)
    ax.set_title("IT-BPO block vs industry headcount", fontsize=9)
    ax.legend(fontsize=6.5)
    ax = axes[2]
    ax.plot(
        q["x"],
        q["itbpo_u25"],
        "o-",
        ms=3,
        label="under-25 share, ISIC 62+63+82 (harmonised LFS)",
    )
    ax.axvline(2022.75, color="grey", ls="--", lw=0.8)
    ax.set_ylim(0, 30)
    ax.set_title("Youth share of the IT-BPO block, quarterly", fontsize=9)
    ax.set_ylabel("percent")
    ax.legend(fontsize=6.5)
    fig.suptitle(
        "Philippines: IT and business-process employment in recent tabulations",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(OUTPUT / "figures" / "phl_sector_leading.png", dpi=140)
    plt.close(fig)
    last = monthly.sort_values(["year", "month"]).tail(1).iloc[0]
    print(
        f"PSA latest: {int(last.year)}-{int(last.month):02d}; N idx {last.N_admin_support_idx:.0f}, J idx {last.J_info_comm_idx:.0f}"
    )
    print(
        lfs[
            [
                "period",
                "itbpo_idx",
                "N_admin_support_idx",
                "J_info_comm_idx",
                "itbpo_u25",
                "n_itbpo",
            ]
        ]
        .round(1)
        .to_string(index=False)
    )
    qq = (
        monthly.groupby("period")[
            ["N_admin_support_idx", "J_info_comm_idx", "total_idx"]
        ]
        .mean()
        .round(1)
    )
    print(qq.tail(8).to_string())


if __name__ == "__main__":
    main()
