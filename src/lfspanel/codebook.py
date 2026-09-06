"""Codebook fingerprints and drift checks.

Statistical agencies change value codes, drop or rename variables and
reclassify categories without always saying so. Two checks run on every
country-quarter:

* ``fingerprint``: for each raw variable in the keep list, the set of observed
  codes (or summary statistics for continuous variables) and the missing
  share, stored as JSON under ``data/processed/codebooks/<ccc>/<period>.json``.
  ``diff_codebooks`` compares consecutive quarters and lists variables that
  appeared or vanished and codes that appeared or vanished, with the share of
  rows they cover.
* ``distribution_drift``: weighted shares of the harmonized categorical
  variables per quarter (ISCO major group, industry, education, employment
  status, formality) with a flag when a share moves by more than a threshold
  against both neighbouring quarters, which catches reclassifications that
  keep the same codes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import pandas as pd

from lfspanel.config import PROCESSED, get_country
from lfspanel.periods import Period

CODEBOOKS = PROCESSED / "codebooks"
MAX_CODES = 400  # variables with more distinct values are summarised, not enumerated
CONTINUOUS_HINT = 40  # distinct integer values above this, densely filling their range,
DENSITY = (
    0.5  # count as continuous (hours, income); sparse ones are classification codes
)
MISSING_TOKENS = {"", "nan", "NaN", "NA", "<NA>", ".", "None"}
DRIFT_VARS = [
    "occup",
    "industrycat10",
    "educat7",
    "empstat",
    "socialsec",
    "lstatus",
    "urban",
]
DRIFT_PP = 3.0  # percentage-point move against both neighbours that gets flagged
# period and identifier variables change every quarter by construction
IGNORE = re.compile(
    r"^(ano4|anio|ano|year|pufsvyyr|quarterno|trimestre|pufsvymo|mes|month|"
    r"mes_central|ano_trimestre|periodo|ronda|codusu|nro_hogar|componente|"
    r"id_vivienda|id_hogar|id_persona|uqno|personno|pufhhnum|pufc01_lno|"
    r"conglomerado|selviv|hogar|c201|llave_panel|uid|diaryid|memberno|"
    r"directorio|secuencia_p|orden|upa|v1008|v1014|v1016|v1028|cd_a|ent|con|"
    r"v_sel|n_hog|h_mud|n_ren|fexp|factor|fac_t300|pondera|weight|p_weights|"
    r"pufpwgtprv|fex_c18|fact_cal|panelm|muestra|estrato|pufpsu|pufrpl|stratum|"
    r"area_geo|nomciudad|codciudad|mes_cal|n_ent|n_pro_viv|v_sel|t_loc)$",
    re.I,
)


def _summary(s: pd.Series) -> dict:
    vals = s.astype("string").str.strip()
    nonmissing = vals.notna() & ~vals.isin(MISSING_TOKENS)
    out = {
        "n": int(len(s)),
        "missing_share": round(1 - nonmissing.mean(), 4) if len(s) else 1.0,
    }
    present = vals[nonmissing]
    nunique = present.nunique()
    numeric = pd.to_numeric(present, errors="coerce")
    if nunique > MAX_CODES or (
        nunique > CONTINUOUS_HINT and numeric.notna().mean() > 0.99
    ):
        out.update(
            {
                "kind": "continuous",
                "n_distinct": int(nunique),
                "min": float(numeric.min()) if numeric.notna().any() else None,
                "max": float(numeric.max()) if numeric.notna().any() else None,
            }
        )
    else:
        counts = present.value_counts()
        out.update(
            {"kind": "codes", "codes": {str(k): int(v) for k, v in counts.items()}}
        )
    return out


def fingerprint(raw: pd.DataFrame, country_key: str, period: Period) -> Path:
    """Write the codebook fingerprint of a raw extract; returns the JSON path."""
    cols = [c for c in raw.columns if c != "source_file" and not IGNORE.match(c)]
    labels = raw.attrs.get("value_labels") or {}
    doc = {
        "country": country_key,
        "period": str(period),
        "rows": int(len(raw)),
        "source_file": str(raw["source_file"].iloc[0])
        if "source_file" in raw and len(raw)
        else "",
        "variables": {c: _summary(raw[c]) for c in cols},
        "labels": {
            c: {str(k): str(v) for k, v in labels[c].items()}
            for c in cols
            if c in labels
        },
    }
    path = CODEBOOKS / country_key / f"{period}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True))
    return path


def load_fingerprints(country_key: str) -> Dict[str, dict]:
    folder = CODEBOOKS / country_key
    if not folder.exists():
        return {}
    docs = {p.stem: json.loads(p.read_text()) for p in folder.glob("*.json")}
    return dict(sorted(docs.items()))


def _label_key(label, code) -> str:
    """Normalised label text: wording-only differences and self-labels do not count."""
    if label is None:
        return ""
    text = (
        re.sub(rf"^\s*{re.escape(str(code))}\s*[.)\-]\s*", "", str(label))
        .strip()
        .lower()
    )
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    if text == "" or text == str(code).strip().lower():
        return ""
    return text


def _row(period, previous, variable, change, detail="", share=None) -> dict:
    return dict(
        period=period, previous=previous, variable=variable, change=change,
        detail=detail, share=share,
    )  # fmt: skip


def diff_codebooks(country_key: str, min_share: float = 0.0) -> pd.DataFrame:
    """Changes between consecutive fingerprints.

    Rows: ``variable_added``, ``variable_removed``, ``codes_added``,
    ``codes_removed`` (with the codes and the share of non-missing rows they
    cover in the quarter where they exist), ``kind_changed`` and
    ``missing_share_jump`` (missing share moved by more than 10 points).
    """
    docs = load_fingerprints(country_key)
    keys = list(docs)
    rows: List[dict] = []
    for prev, cur in zip(keys, keys[1:]):
        a = {k: v for k, v in docs[prev]["variables"].items() if not IGNORE.match(k)}
        b = {k: v for k, v in docs[cur]["variables"].items() if not IGNORE.match(k)}
        la, lb = docs[prev].get("labels", {}), docs[cur].get("labels", {})
        for v in sorted(set(la) & set(lb)):
            changed = {
                k
                for k in set(la[v]) | set(lb[v])
                if _label_key(la[v].get(k), k) != _label_key(lb[v].get(k), k)
            }
            if changed:
                detail = "; ".join(
                    f"{k}: {la[v].get(k, '-')!r} -> {lb[v].get(k, '-')!r}"
                    for k in sorted(changed)[:6]
                )
                rows.append(_row(cur, prev, v, "labels_changed", detail[:300]))
        for v in sorted(set(b) - set(a)):
            rows.append(
                dict(period=cur, previous=prev, variable=v, change="variable_added")
            )
        for v in sorted(set(a) - set(b)):
            rows.append(
                dict(period=cur, previous=prev, variable=v, change="variable_removed")
            )
        for v in sorted(set(a) & set(b)):
            va, vb = a[v], b[v]
            if va.get("kind") != vb.get("kind"):
                detail = f"{va.get('kind')} -> {vb.get('kind')}"
                rows.append(_row(cur, prev, v, "kind_changed", detail))
                continue
            if abs(va["missing_share"] - vb["missing_share"]) > 0.10:
                detail = f"{va['missing_share']:.2f} -> {vb['missing_share']:.2f}"
                rows.append(_row(cur, prev, v, "missing_share_jump", detail))
            if va.get("kind") != "codes":
                continue
            ca, cb = va["codes"], vb["codes"]
            tot_a, tot_b = max(sum(ca.values()), 1), max(sum(cb.values()), 1)
            added = {k: n for k, n in cb.items() if k not in ca}
            removed = {k: n for k, n in ca.items() if k not in cb}
            share_added = sum(added.values()) / tot_b
            share_removed = sum(removed.values()) / tot_a
            if added and share_added >= min_share:
                detail = ",".join(sorted(added)[:30])
                rows.append(
                    _row(cur, prev, v, "codes_added", detail, round(share_added, 4))
                )
            if removed and share_removed >= min_share:
                detail = ",".join(sorted(removed)[:30])
                rows.append(
                    _row(cur, prev, v, "codes_removed", detail, round(share_removed, 4))
                )
    cols = ["period", "previous", "variable", "change", "detail", "share"]
    return pd.DataFrame(rows, columns=cols)


def distribution_drift(
    con: duckdb.DuckDBPyConnection,
    country_key: Optional[str] = None,
    variables: Optional[List[str]] = None,
    threshold_pp: float = DRIFT_PP,
) -> pd.DataFrame:
    """Weighted category shares by country-quarter with a drift flag.

    A share is flagged when it moves by more than ``threshold_pp`` points
    against both the previous and the next quarter in the same direction
    (a level shift), or by more than twice the threshold against the previous
    quarter alone (a spike at the end of the series).
    """
    variables = variables or DRIFT_VARS
    where = (
        f"WHERE countrycode = '{get_country(country_key).ccc}'" if country_key else ""
    )
    parts = []
    for v in variables:
        base = (
            "employed"
            if v in ("occup", "industrycat10", "empstat", "socialsec")
            else "harmonized"
        )
        q = f"""
            SELECT countrycode, period, '{v}' AS variable,
                   CAST({v} AS VARCHAR) AS category,
                   100.0 * sum(weight)
                       / sum(sum(weight)) OVER (PARTITION BY countrycode, period)
                       AS share
            FROM {base} {where}
            GROUP BY 1, 2, 3, 4
        """
        parts.append(con.execute(q).df())
    df = pd.concat(parts, ignore_index=True)
    df["category"] = df["category"].fillna("NA")
    df = df.sort_values(["countrycode", "variable", "category", "period"])
    g = df.groupby(["countrycode", "variable", "category"])["share"]
    df["d_prev"] = df["share"] - g.shift(1)
    df["d_next"] = g.shift(-1) - df["share"]
    level_shift = (df["d_prev"].abs() > threshold_pp) & (
        df["d_next"].abs() <= threshold_pp
    )
    spike = (
        (df["d_prev"].abs() > threshold_pp)
        & (df["d_next"].abs() > threshold_pp)
        & ((df["d_prev"] * df["d_next"]) < 0)
    )
    end_jump = (df["d_prev"].abs() > 2 * threshold_pp) & df["d_next"].isna()
    df["flag"] = ""
    df.loc[level_shift, "flag"] = "level_shift"
    df.loc[spike, "flag"] = "spike"
    df.loc[end_jump, "flag"] = "end_jump"
    return df.reset_index(drop=True)
