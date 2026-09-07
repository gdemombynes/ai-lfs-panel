"""Read one quarter of the PLFS person file from a MoSPI Stata release.

Every release ships a person-level ``.dta`` (first-visit records in the
calendar-year files; all visits in the 2025 quarterly file) whose variable
names changed three times: ``b6q5_cperv1``-style names in 2021-2023,
descriptive names in 2024 (``CWS_Status_Code``) and short names from 2025
(``acws``). ``ALIASES`` maps each release onto the 2025 names, which are the
canonical ones in ``resources/keep_lists/ind.txt``.

Quarter labels run across the July-June survey year in the old design, so
``QUARTER_LABELS`` translates them to calendar quarters per release. The
calendar-year files carry the survey month only in the household file; it is
merged in here.
"""

from __future__ import annotations

import re
import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from lfspanel.fetch.ind import Release, find_zip, release_for
from lfspanel.periods import Period

CHUNK = 200_000
DAYS = range(1, 8)

# quarter label in the file -> calendar quarter, per release
QUARTER_LABELS: Dict[str, Dict[str, int]] = {
    "cy2021": {"Q7": 1, "Q8": 2, "Q1": 3, "Q2": 4},
    "cy2022": {"Q3": 1, "Q4": 2, "Q5": 3, "Q6": 4},
    "cy2023": {"Q7": 1, "Q8": 2, "Q1": 3, "Q2": 4},
    "cy2024": {"Q3": 1, "Q4": 2, "Q5": 3, "Q6": 4},
    "cy2025": {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4},
    "q2025": {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4},
}

# canonical name -> variable name in the 2021-2023 releases (block/item names)
_BQ = {
    "qtr": "qtr_cperv1", "visit": "visit_cperv1", "sec": "b1q3_cperv1",
    "st": "state_cperv1", "dc": "distcode_cperv1", "mfsu": "b1q1_cperv1",
    "sss": "b1q14_cperv1", "ssu": "b1q15_cperv1", "srl": "b4q1_cperv1",
    "panel": "panel_cperv1", "sex": "b4q5_cperv1", "age": "b4q6_perv1",
    "gedu_lvl": "b4q8_cperv1", "acws": "b6q5_cperv1", "aind_cws": "b6q6_cperv1",
    "ocu_cws": "b6q7_cperv1", "ern_reg": "b6q9_cperv1", "ern_self": "b6q10_cperv1",
    "nss": "nss_cperv1", "nsc": "nsc_cperv1", "mult": "mult_cperv1",
    "no_qtr": "no_qtr_cperv1",
    # daily items: part k of block 6 item 3 is day 8-k of the reference week
    "hr7": "b6q7_act2_3pt1_cperv1", "hr6": "b6q7_3pt2_cperv1",
    "hr5": "b6q7_3pt3_cperv1", "hr4": "b6q7_3pt4_cperv1",
    "hr3": "b6q7_3pt5_cperv1", "hr2": "b6q7_3pt6_cperv1",
    "hr1": "b6q7_act2_3pt7_cperv1",
    "ahr7": "b6q8_3pt1_cperv1", "ahr6": "b6q8_3pt2_cperv1",
    "ahr5": "b6q8_3pt3_cperv1", "ahr4": "b6q8_3pt4_cperv1",
    "ahr3": "b6q8_3pt5_cperv1", "ahr2": "b6q8_3pt6_cperv1",
    "ahr1": "b6q8_act2_3pt7_cperv1",
}  # fmt: skip
for _k in DAYS:
    _BQ[f"ern1{8 - _k}"] = f"b6q9_3pt{_k}_cperv1"
    _BQ[f"ern2{8 - _k}"] = f"b6q9_act2_3pt{_k}_cperv1"

_BQ21 = {
    k: v
    for k, v in _BQ.items()
    if not re.match(r"^(hr|ahr|ern1|ern2)\d$", k) and k != "no_qtr"
}
_BQ21["age"] = "b4q6_cperv1"

_DESC = {
    "qtr": "Quarter", "visit": "Visit", "sec": "Sector", "st": "State_UT_Code",
    "dc": "District_Code", "mfsu": "FSU", "sss": "Second_Stage_Stratum_No",
    "ssu": "Sample_Household_Number", "srl": "Person_Serial_No", "panel": "Panel",
    "sex": "Sex", "age": "Age", "gedu_lvl": "General_Education_Level",
    "acws": "CWS_Status_Code", "aind_cws": "CWS_Industry_Code",
    "ocu_cws": "CWS_Occupation_Code", "ern_reg": "CWS_Earnings_Salaried",
    "ern_self": "CWS_Earnings_SelfEmployed", "nss": "Ns_Count_Sector_Subsample",
    "nsc": "Ns_Count_Sector_Substratum", "mult": "Subsample_Multiplier",
    "no_qtr": "State_Sector_Stratum_Substra",
}  # fmt: skip
for _d in DAYS:
    _DESC[f"hr{_d}"] = f"Day{_d}_Total_Hours"
    _DESC[f"ahr{_d}"] = f"Day{_d}_Additional_Work_Hours"
    _DESC[f"ern1{_d}"] = f"Day{_d}_Act1_Wage"
    _DESC[f"ern2{_d}"] = f"Day{_d}_Act2_Wage"

ALIASES: Dict[str, Dict[str, str]] = {
    "cy2021": _BQ21,
    "cy2022": _BQ,
    "cy2023": _BQ,
    "cy2024": _DESC,
    "cy2025": {},
    "q2025": {},
}
# household file: survey month and the join keys, for releases without a
# person-level month
HH_ALIASES: Dict[str, Dict[str, str]] = {
    "cy2021": {"qtr": "qtr_chhv1", "mfsu": "b1q1_chhv1", "sss": "b1q14_chhv1",
               "ssu": "b1q15_chhv1", "month": "b1q9_chhv1"},
    "cy2022": {"qtr": "qtr_chhv1", "mfsu": "b1q1_chhv1", "sss": "b1q14_chhv1",
               "ssu": "b1q15_chhv1", "month": "b1q9_chhv1"},
    "cy2023": {"qtr": "qtr_chhv1", "mfsu": "b1q1_chhv1", "sss": "b1q14_chhv1",
               "ssu": "b1q15_chhv1", "month": "b1q9_chhv1"},
    "cy2024": {"qtr": "Quarter", "mfsu": "FSU", "sss": "Second_Stage_Stratum_No",
               "ssu": "Sample_Household_Number", "month": "Month_of_Survey"},
}  # fmt: skip
OPTIONAL = {"month", "nss", "no_qtr", "ern_reg", "ern_self"} | {
    f"{p}{d}" for p in ("hr", "ahr", "ern1", "ern2") for d in DAYS
}


def keep_list() -> List[str]:
    text = (files("lfspanel") / "resources" / "keep_lists" / "ind.txt").read_text()
    return [
        ln.split("#", 1)[0].strip()
        for ln in text.splitlines()
        if ln.split("#", 1)[0].strip()
    ]


def quarter_label(rel: Release, period: Period) -> str:
    labels = QUARTER_LABELS[rel.label]
    for label, q in labels.items():
        if q == period.quarter:
            return label
    raise KeyError(f"{period} not in release {rel.label}")


def _member(z: zipfile.ZipFile, pattern: str) -> str:
    for name in z.namelist():
        base = name.replace("\\", "/").split("/")[-1]
        if re.search(pattern, base, flags=re.I):
            return name
    raise FileNotFoundError(f"No member matching {pattern!r} in {z.filename}")


def _extract(z: zipfile.ZipFile, member: str, tmpdir: str) -> Path:
    out = Path(tmpdir) / Path(member).name
    with z.open(member) as src, open(out, "wb") as dst:
        for block in iter(lambda: src.read(1 << 22), b""):
            dst.write(block)
    return out


def _to_text(s: pd.Series) -> pd.Series:
    """Codes as trimmed strings; numeric storage rounded to integers."""
    if pd.api.types.is_numeric_dtype(s):
        return s.round().astype("Int64").astype("string").fillna("")
    return s.astype("string").str.strip().fillna("")


def _read_selected(
    path: Path, wanted: Dict[str, str], qtr_key: str, label: str
) -> pd.DataFrame:
    """Rows of one quarter label, chunked so the 1 GB 2025 file fits in memory."""
    qtr_col = wanted[qtr_key]
    parts = []
    with pd.read_stata(
        path,
        columns=list(wanted.values()),
        chunksize=CHUNK,
        convert_categoricals=False,
    ) as reader:
        for chunk in reader:
            q = chunk[qtr_col].astype("string").str.strip()
            parts.append(chunk[q == label])
    if parts:
        df = pd.concat(parts, ignore_index=True)
    else:
        df = pd.DataFrame(columns=list(wanted.values()))
    return df.rename(columns={v: k for k, v in wanted.items()})


def read_raw(
    period: Period, nrows: Optional[int] = None, path: Optional[Path] = None
) -> pd.DataFrame:
    rel = release_for(period)
    src = path or find_zip(period)
    aliases = ALIASES[rel.label]
    keep = keep_list()
    label = quarter_label(rel, period)
    with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as tmp:
        pmember = _member(z, rel.person_member)
        ppath = _extract(z, pmember, tmp)
        with pd.read_stata(ppath, iterator=True) as reader:
            available = set(reader.variable_labels())
        wanted = {c: aliases.get(c, c) for c in keep if aliases.get(c, c) in available}
        missing = [c for c in keep if c not in wanted]
        if set(missing) - OPTIONAL:
            bad = sorted(set(missing) - OPTIONAL)
            raise KeyError(f"{pmember}: missing columns {bad}")
        df = _read_selected(ppath, wanted, "qtr", label)
        if "month" not in df.columns and rel.label in HH_ALIASES:
            hh_alias = HH_ALIASES[rel.label]
            hpath = _extract(z, _member(z, rel.hh_member), tmp)
            hh = _read_selected(hpath, hh_alias, "qtr", label)
            keys = ["mfsu", "sss", "ssu"]
            for c in keys:
                hh[c] = _to_text(hh[c])
                df[c] = _to_text(df[c])
            hh = hh.drop_duplicates(keys)[keys + ["month"]]
            df = df.merge(hh, on=keys, how="left")
    if nrows:
        df = df.head(nrows)
    for c in missing:
        if c not in df.columns:
            df[c] = ""
    for c in df.columns:
        if c == "mult":
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
        else:
            df[c] = _to_text(df[c])
    df["plfs_release"] = rel.label
    df["source_file"] = f"{Path(src).name}:{Path(pmember).name}"
    return df[keep + ["plfs_release", "source_file"]].reset_index(drop=True)
