"""Build the South Africa occupation crosswalks from external sources.

    python scripts/91_build_zaf_crosswalks.py

Inputs (data/external/crosswalks/):
  Correspondence_EN_ISCO_88_to_ISCO_08.xlsx   ILO correspondence, unit groups
  isco88_sasco03_mapping.dta                  GLD, SASCO 2003 minor groups to ISCO-88

Outputs (src/lfspanel/resources/crosswalks/):
  isco88_to_isco08.csv     isco88 (4 digits) -> isco08 prefix, digits, rule
  sasco2003_to_isco88.csv  sasco3 (3 digits) -> isco88 prefix (2 or 3 digits)

Rule for ISCO-88 unit groups: when the ILO table lists a target without the
"partial" flag the whole group moves there (4 digits). Otherwise the targets
sharing the longest leading digits with the source code are kept (ISCO-08
retained most of the ISCO-88 numbering, so these hold the bulk of the group)
and their deepest common prefix is recorded with its length.
"""

from __future__ import annotations

import os

import pandas as pd

from lfspanel.config import EXTERNAL, ROOT

CROSSWALKS = ROOT / "src" / "lfspanel" / "resources" / "crosswalks"


def isco88_to_isco08() -> pd.DataFrame:
    x = pd.read_excel(
        EXTERNAL / "crosswalks" / "Correspondence_EN_ISCO_88_to_ISCO_08.xlsx",
        sheet_name="ISCO-88 to 08",
        dtype=str,
    )
    x = x.iloc[:, :4]
    x.columns = ["title88", "isco88", "isco08", "part"]
    x = x[x["isco88"].notna() & x["isco08"].notna()].copy()
    x["isco88"] = x["isco88"].str.strip().str.zfill(4)
    x["isco08"] = x["isco08"].str.strip().str.zfill(4)
    x["part"] = x["part"].fillna("").str.strip().str.lower()
    rows = []
    for code, g in x.groupby("isco88"):
        whole = g[g["part"] == ""]
        pool = whole if len(whole) else g
        rule = (
            "whole" if len(whole) == 1 else ("whole-multi" if len(whole) else "partial")
        )
        targets = sorted(set(pool["isco08"]))
        prefix = os.path.commonprefix(targets)
        if len(targets) > 1 and len(prefix) < 3:
            # keep the targets that resemble the source code most (ISCO-08 kept
            # most ISCO-88 numbering), then their common prefix
            shared = [len(os.path.commonprefix([code, t])) for t in targets]
            if max(shared) >= 1:
                best = [t for t, n in zip(targets, shared) if n == max(shared)]
                prefix, rule = os.path.commonprefix(best), rule + "-similar"
        rows.append(
            {
                "isco88": code,
                "isco08": prefix.ljust(4, "0") if prefix else "",
                "digits": len(prefix),
                "rule": rule,
                "targets": ",".join(sorted(set(g["isco08"]))),
            }
        )
    return pd.DataFrame(rows)


def sasco2003_to_isco88() -> pd.DataFrame:
    d = pd.read_stata(
        EXTERNAL / "crosswalks" / "isco88_sasco03_mapping.dta",
        convert_categoricals=False,
    )
    d = d[d["isco_88"].astype(str).str.strip().str.match(r"^\d+$")]
    out = pd.DataFrame(
        {
            "sasco3": d["occupcat_isco"].astype(str).str.zfill(3),
            "isco88": d["isco_88"].astype(str).str.strip().str.rstrip("0"),
            "sasco_title": d["sasco_occup"].str.strip(),
        }
    )
    out["isco88"] = out["isco88"].where(out["isco88"] != "", "0")
    out["digits"] = out["isco88"].str.len()
    return out


def main() -> None:
    a = isco88_to_isco08()
    a.to_csv(CROSSWALKS / "isco88_to_isco08.csv", index=False)
    digits = a["digits"].value_counts().to_dict()
    print(f"isco88_to_isco08: {len(a)} unit groups, digits {digits}")
    b = sasco2003_to_isco88()
    b.to_csv(CROSSWALKS / "sasco2003_to_isco88.csv", index=False)
    digits = b["digits"].value_counts().to_dict()
    print(f"sasco2003_to_isco88: {len(b)} minor groups, digits {digits}")


if __name__ == "__main__":
    main()
