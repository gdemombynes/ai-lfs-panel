"""IT and business-process services (ISIC 62, 63, 82) by country and year.

Annual averages of employment in the sector, its IT (62+63) and BPO (82)
parts, the professional (ISCO 1-3) and clerical/service (ISCO 4-5)
occupations within it, and the under-25 and under-30 shares, indexed to
2022. South Africa's SIC 88 lumps business services, so it is ISIC 62 only;
Mexico's ENOE classifier does not separate computer services, so it uses
ENOE code 5611 (business support and employment services). Nigeria (no
2022) and India's NCO-2004 quarters are left out.

Writes output/tables/itbpo_by_country.csv and
output/figures/itbpo_by_country.png.
"""

from __future__ import annotations

import duckdb
import matplotlib
import pandas as pd

from lfspanel.config import OUTPUT, PROCESSED

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DB = PROCESSED / "panel.duckdb"
ORDER = [
    "BRA",
    "COL",
    "MEX",
    "ARG",
    "ECU",
    "PER",
    "URY",
    "BOL",
    "ZAF",
    "GEO",
    "PHL",
    "IND",
]
DEFINITION = {
    "ZAF": "ISIC 62 only (SIC 88 lumps business services)",
    "MEX": "ENOE 5611 business support and employment services (IT not separable)",
}
TITLE = {"ZAF": " (ISIC 62 only)", "MEX": " (ENOE 5611 only)"}

SQL = """
with e as (
  select countrycode, substr(period, 1, 4) yr, period, weight, age, occup_isco,
    case
      when countrycode = 'MEX' then case when industry_orig = '5611' then 'bpo' end
      when substr(industrycat_isic, 1, 2) in ('62', '63') then 'it'
      when substr(industrycat_isic, 1, 2) = '82' and countrycode <> 'ZAF' then 'bpo'
    end seg,
    case when substr(occup_isco, 1, 1) in ('1', '2', '3') then 'prof'
         when substr(occup_isco, 1, 1) in ('4', '5') then 'cler_serv' else 'other' end og
  from employed
  where source = 'own' and countrycode <> 'NGA'
    and not (countrycode = 'IND' and period < '2021Q3'))
select countrycode, yr, count(distinct period) nq,
  sum(weight) / count(distinct period) / 1e3 emp_all_k,
  sum(case when seg is not null then weight end) / count(distinct period) / 1e3 itbpo_k,
  count(case when seg is not null then 1 end) n_itbpo,
  sum(case when seg = 'it' then weight end) / count(distinct period) / 1e3 it_k,
  sum(case when seg = 'bpo' then weight end) / count(distinct period) / 1e3 bpo_k,
  sum(case when seg is not null and og = 'prof' then weight end) / count(distinct period) / 1e3 itbpo_prof_k,
  sum(case when seg is not null and og = 'cler_serv' then weight end) / count(distinct period) / 1e3 itbpo_cler_k,
  100 * sum(case when seg is not null and age < 25 then weight end) / sum(case when seg is not null then weight end) u25_itbpo,
  100 * sum(case when seg is not null and age < 30 then weight end) / sum(case when seg is not null then weight end) u30_itbpo,
  100 * sum(case when age < 25 then weight end) / sum(weight) u25_all
from e group by 1, 2 order by 1, 2
"""


def build() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    t = con.execute(SQL).df()
    con.close()
    for c in ["itbpo_k", "it_k", "bpo_k", "itbpo_prof_k", "itbpo_cler_k", "emp_all_k"]:
        base = t[t["yr"] == "2022"].set_index("countrycode")[c]
        t[c.replace("_k", "_idx")] = 100 * t[c] / t["countrycode"].map(base)
    t["itbpo_share_pct"] = 100 * t["itbpo_k"] / t["emp_all_k"]
    t["definition"] = t["countrycode"].map(lambda c: DEFINITION.get(c, "ISIC 62+63+82"))
    return t


def plot(t: pd.DataFrame, path) -> None:
    codes = [c for c in ORDER if c in set(t["countrycode"])]
    ncol = 6
    nrow = -(-len(codes) // ncol)
    fig, axes = plt.subplots(2 * nrow, ncol, figsize=(3.2 * ncol, 5.5 * nrow))
    for i, cc in enumerate(codes):
        r, c = divmod(i, ncol)
        s = t[t["countrycode"] == cc].sort_values("yr")
        ax = axes[2 * r][c]
        ax.plot(s["yr"], s["itbpo_idx"], marker="o", label="IT-BPO industries")
        ax.plot(
            s["yr"],
            s["itbpo_cler_idx"],
            marker="s",
            ms=3,
            label="of which clerical/service",
        )
        ax.plot(s["yr"], s["emp_all_idx"], color="grey", label="all employment")
        ax.axhline(100, color="grey", lw=0.6)
        ax.set_title(cc + TITLE.get(cc, ""), fontsize=10)
        ax.set_ylim(55, 150)
        ax2 = axes[2 * r + 1][c]
        ax2.plot(s["yr"], s["u25_itbpo"], marker="o", label="under-25 share, IT-BPO")
        ax2.plot(s["yr"], s["u25_all"], color="grey", label="under-25 share, all")
        ax2.set_ylim(0, 45)
    for r in range(nrow):
        axes[2 * r][0].set_ylabel("employment, 2022 = 100")
        axes[2 * r + 1][0].set_ylabel("share under 25, %")
    axes[0][0].legend(fontsize=7)
    axes[1][0].legend(fontsize=7)
    for i in range(len(codes), nrow * ncol):
        r, c = divmod(i, ncol)
        axes[2 * r][c].axis("off")
        axes[2 * r + 1][c].axis("off")
    fig.suptitle(
        "IT and business-process services (ISIC 62, 63, 82): employment and youth share, annual averages",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    t = build()
    tables = OUTPUT / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    t.round(3).to_csv(tables / "itbpo_by_country.csv", index=False)
    (OUTPUT / "figures").mkdir(parents=True, exist_ok=True)
    plot(t, OUTPUT / "figures" / "itbpo_by_country.png")
    cols = ["countrycode", "yr", "n_itbpo", "itbpo_share_pct", "itbpo_idx", "itbpo_prof_idx",
            "itbpo_cler_idx", "emp_all_idx", "u25_itbpo", "u25_all"]  # fmt: skip
    print(
        t[t["yr"].isin(["2022", "2025", "2026"])][cols].round(1).to_string(index=False)
    )


if __name__ == "__main__":
    main()
