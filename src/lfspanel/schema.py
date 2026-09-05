"""Target schema (GLD variable names) and frame validation."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

# name -> (pandas dtype, description). Order is the column order on disk.
TARGET_SCHEMA: Dict[str, tuple] = {
    "countrycode": ("string", "ISO3 country code"),
    "source": ("string", "own | gld"),
    "period": ("string", "Calendar quarter, e.g. 2023Q1 (partition key)"),
    "year": ("Int16", "Survey reference year"),
    "int_year": ("Int16", "Interview year"),
    "int_month": ("Int8", "Interview month, NA if survey does not record it"),
    "wave": ("string", "Q1..Q4 or M01..M12"),
    "hhid": ("string", "Household id"),
    "pid": ("string", "Person id"),
    "rotation_group": ("string", "Rotation panel group, NA if not a panel"),
    "visit_no": ("Int8", "Visit number within the panel"),
    "weight": ("float64", "Person weight for the reference quarter"),
    "urban": ("Int8", "1 urban, 0 rural"),
    "subnatid1": ("string", "First subnational level, 'code - name'"),
    "age": ("Int16", "Age in years"),
    "male": ("Int8", "1 male, 0 female"),
    "educat4": ("Int8", "GLD 4-level education"),
    "educat7": ("Int8", "GLD 7-level education"),
    "minlaborage": ("Int8", "Minimum age of the labor module"),
    "lstatus": ("Int8", "1 employed, 2 unemployed, 3 not in labor force"),
    "potential_lf": ("Int8", "Potential labor force (NLF only)"),
    "underemployment": ("Int8", "Time-related underemployment (employed only)"),
    "nlfreason": ("Int8", "1 student 2 housekeeper 3 retired 4 disabled 5 other"),
    "empstat": ("Int8", "1 paid employee 2 unpaid 3 employer 4 self-employed 5 other"),
    "ocusec": ("Int8", "1 public 2 private 3 SOE 4 public/SOE undistinguished"),
    "industry_orig": ("string", "National industry code as in the survey"),
    "industrycat_isic": ("string", "ISIC Rev.4, 4 chars, trailing zeros"),
    "isic_digits": ("Int8", "Reliable ISIC digits (1-4)"),
    "industrycat10": ("Int8", "GLD 10-category industry"),
    "industrycat4": ("Int8", "GLD 4-category industry"),
    "occup_orig": ("string", "National occupation code as in the survey"),
    "occup_isco": ("string", "ISCO-08, 4 chars, trailing zeros"),
    "occup_isco_digits": ("Int8", "Reliable ISCO digits (1-4)"),
    "occup": ("Int8", "ISCO major group 1-9, 0 armed forces"),
    "occup_skill": ("Int8", "1 low 2 medium 3 high"),
    "wage_no_compen": ("float64", "Last wage payment, main job"),
    "unitwage": ("Int8", "GLD wage time unit (5 monthly)"),
    "whours": ("float32", "Hours worked last week, main job"),
    "contract": ("Int8", "1 has written contract / formal registration"),
    "socialsec": ("Int8", "1 contributes to social security"),
    "firmsize_l": ("Int16", "Firm size lower bracket"),
    "firmsize_u": ("Int16", "Firm size upper bracket"),
    "tenure_months": (
        "float32",
        "Months in current main job (band midpoint if banded)",
    ),
    "tenure_lt12": ("Int8", "1 if in current main job less than 12 months"),
    "source_file": ("string", "Raw file the row came from"),
    "raw_release": ("string", "Release / last-modified date of the raw file"),
    "harmonize_version": ("string", "lfspanel harmonization version"),
}

COLUMNS: List[str] = list(TARGET_SCHEMA)

CODE_DOMAINS = {
    "urban": {0, 1},
    "male": {0, 1},
    "educat4": {1, 2, 3, 4},
    "educat7": {1, 2, 3, 4, 5, 6, 7},
    "lstatus": {1, 2, 3},
    "potential_lf": {0, 1},
    "underemployment": {0, 1},
    "nlfreason": {1, 2, 3, 4, 5},
    "empstat": {1, 2, 3, 4, 5},
    "ocusec": {1, 2, 3, 4},
    "industrycat10": set(range(1, 11)),
    "industrycat4": {1, 2, 3, 4},
    "occup": set(range(0, 10)),
    "occup_skill": {1, 2, 3},
    "unitwage": set(range(1, 11)),
    "contract": {0, 1},
    "socialsec": {0, 1},
    "tenure_lt12": {0, 1},
    "isic_digits": {1, 2, 3, 4},
    "occup_isco_digits": {1, 2, 3, 4},
}

LABOR_VARS_EMPLOYED_ONLY = [
    "empstat",
    "ocusec",
    "industry_orig",
    "industrycat_isic",
    "industrycat10",
    "industrycat4",
    "occup_orig",
    "occup_isco",
    "occup",
    "occup_skill",
    "whours",
    "contract",
    "socialsec",
    "tenure_lt12",
]


def _cast(series: pd.Series, dtype: str) -> pd.Series:
    """Cast tolerant of object columns holding pd.NA / NaN / numpy scalars."""
    if dtype == "string":
        s = series.astype("object").where(series.notna(), None)
        return s.astype("string")
    numeric = pd.to_numeric(series, errors="coerce")
    if dtype.startswith("Int"):
        return numeric.round().astype(dtype)
    return numeric.astype(dtype)


def cast_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with every schema column present, ordered and typed."""
    out = pd.DataFrame(index=df.index)
    for col, (dtype, _) in TARGET_SCHEMA.items():
        if col in df.columns:
            out[col] = _cast(df[col], dtype)
        else:
            fill = float("nan") if dtype.startswith("float") else pd.NA
            out[col] = pd.Series(fill, index=df.index, dtype=dtype)
    return out


def validate_frame(df: pd.DataFrame, strict: bool = True) -> List[str]:
    """Check a harmonized frame; return problems (and raise if ``strict``)."""
    problems: List[str] = []
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {missing}")
        if strict:
            raise ValueError("; ".join(problems))
        return problems
    for col, domain in CODE_DOMAINS.items():
        vals = df[col].dropna()
        bad = sorted(set(vals.unique()) - domain)
        if bad:
            problems.append(f"{col}: values outside domain {bad[:10]}")
    if (df["weight"].dropna() <= 0).any():
        problems.append("weight: non-positive values")
    if df["weight"].isna().any():
        problems.append("weight: missing values")
    under = df["age"] < df["minlaborage"]
    if df.loc[under, "lstatus"].notna().any():
        problems.append("lstatus set below minlaborage")
    employed = df["lstatus"] == 1
    if df.loc[~employed, "occup_isco"].notna().any():
        problems.append("occup_isco present for non-employed rows")
    if df.loc[~employed, "industrycat_isic"].notna().any():
        problems.append("industrycat_isic present for non-employed rows")
    has_isco = df["occup_isco"].notna()
    if has_isco.any():
        lengths = df.loc[has_isco, "occup_isco"].str.len()
        if (lengths != 4).any():
            problems.append("occup_isco: not all codes are 4 characters")
        first = pd.to_numeric(
            df.loc[has_isco, "occup_isco"].str[0], errors="coerce"
        ).astype("Int8")
        occ = df.loc[has_isco, "occup"].astype("Int8")
        mism = int(((first != occ) | occ.isna() | first.isna()).sum())
        if mism:
            problems.append(
                f"occup disagrees with occup_isco first digit in {mism} rows"
            )
    has_isic = df["industrycat_isic"].notna()
    if has_isic.any():
        lengths = df.loc[has_isic, "industrycat_isic"].str.len()
        if (lengths != 4).any():
            problems.append("industrycat_isic: not all codes are 4 characters")
    if strict and problems:
        raise ValueError("; ".join(problems))
    return problems
