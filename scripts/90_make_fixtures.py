"""Write small raw extracts under tests/fixtures/ for unit tests.

    python scripts/90_make_fixtures.py --country bra --period 2025Q1 --n 60
    python scripts/90_make_fixtures.py --country mex --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country col --period 2025M01 --n 500
    python scripts/90_make_fixtures.py --country arg --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country ecu --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country per --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country zaf --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country geo --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country phl --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country nga --period 2024Q3 --n 400
    python scripts/90_make_fixtures.py --country ind --period 2025Q2 --n 400
    python scripts/90_make_fixtures.py --country ury --period 2025Q1 --n 400

Fixtures are random samples of public microdata rows in the original file
layout, so reader and harmonizer tests exercise the real formats.
"""

from __future__ import annotations

import argparse
import random
import re
import zipfile
from pathlib import Path

import pandas as pd

from lfspanel.config import ROOT, get_country
from lfspanel.periods import Period

FIXTURES = ROOT / "tests" / "fixtures"


def make_bra(period: Period, n: int, seed: int = 7) -> Path:
    from lfspanel.fetch.bra import find_zip

    rng = random.Random(seed)
    out = FIXTURES / "bra" / "PNADC_sample.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    keep = []
    with zipfile.ZipFile(find_zip(period)) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".txt"))
        with z.open(member) as f:
            for i, line in enumerate(f):
                if i < 200_000 and rng.random() < 0.0004:
                    keep.append(line)
                if len(keep) >= n:
                    break
    out.write_bytes(b"".join(keep))
    return out


def _subset_csv(
    src: zipfile.ZipFile, member: str, keys: list, selected: set, sep: str
) -> bytes:
    t = pd.read_csv(
        src.open(member), sep=sep, dtype=str, keep_default_na=False, encoding="latin-1"
    )
    t = t[[tuple(r) in selected for r in t[keys].values.tolist()]]
    return t.to_csv(index=False, sep=sep, lineterminator="\n").encode("latin-1")


def make_mex(period: Period, n: int, seed: int = 11) -> Path:
    from lfspanel.fetch.mex import find_zip
    from lfspanel.read.mex import KEYS

    src = zipfile.ZipFile(find_zip(period))
    members = {
        k: next(m for m in src.namelist() if k in m.upper())
        for k in ("SDEM", "COE1", "COE2")
    }
    sdem = pd.read_csv(
        src.open(members["SDEM"]), dtype=str, keep_default_na=False, encoding="latin-1"
    )
    sample = sdem.sample(n, random_state=seed)
    selected = set(map(tuple, sample[KEYS].values.tolist()))
    out = FIXTURES / "mex" / Path(src.filename).name
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            Path(members["SDEM"]).name,
            sample.to_csv(index=False, lineterminator="\n").encode("latin-1"),
        )
        for k in ("COE1", "COE2"):
            z.writestr(
                Path(members[k]).name, _subset_csv(src, members[k], KEYS, selected, ",")
            )
    return out


def make_col(month: Period, n: int, seed: int = 11) -> Path:
    from lfspanel.fetch.col import find_zip
    from lfspanel.read.col import KEYS, MODULES

    src = zipfile.ZipFile(find_zip(month))
    cg_member = next(
        m
        for m in src.namelist()
        if m.startswith(MODULES["cg"]) and m.upper().endswith(".CSV")
    )
    cg = pd.read_csv(
        src.open(cg_member),
        sep=";",
        dtype=str,
        keep_default_na=False,
        encoding="latin-1",
    )
    sample = cg.sample(n, random_state=seed)
    selected = set(map(tuple, sample[KEYS].values.tolist()))
    out = FIXTURES / "col" / f"geih_{month.year}_{month.month:02d}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "CSV/Caracteristicas generales, seguridad social en salud y educacion.CSV",
            sample.to_csv(index=False, sep=";", lineterminator="\n").encode("latin-1"),
        )
        for key in ("ft", "oc", "no"):
            member = next(
                m
                for m in src.namelist()
                if m.startswith(MODULES[key]) and m.upper().endswith(".CSV")
            )
            z.writestr(member, _subset_csv(src, member, KEYS, selected, ";"))
    return out


def make_arg(period: Period, n: int, seed: int = 11) -> Path:
    """Sample whole households from the EPH usu_individual text file."""
    from lfspanel.fetch.arg import find_zip

    src = zipfile.ZipFile(find_zip(period))
    member = next(m for m in src.namelist() if "individual" in m.lower())
    t = pd.read_csv(
        src.open(member), sep=";", dtype=str, keep_default_na=False, encoding="latin-1"
    )
    hh = t["CODUSU"].drop_duplicates().sample(frac=1, random_state=seed)
    keep = set(hh.head(max(1, n // 3)))
    sample = t[t["CODUSU"].isin(keep)].head(n)
    out = FIXTURES / "arg" / f"EPH_usu_{period.quarter}_Trim_{period.year}_txt.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            f"usu_individual_T{period.quarter}{str(period.year)[2:]}.txt",
            sample.to_csv(index=False, sep=";", lineterminator="\n").encode("latin-1"),
        )
    return out


def _sample_stata_like(
    src_zip: Path, member: str, reader, writer, n: int, seed: int, suffix: str
) -> bytes:
    """Read a .sav/.dta member, sample n rows, write back in the same format."""
    import tempfile

    with zipfile.ZipFile(src_zip) as z, tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"in{suffix}"
        path.write_bytes(z.read(member))
        df, meta = reader(str(path))
        sample = df.sample(min(n, len(df)), random_state=seed)
        out = Path(tmp) / f"out{suffix}"
        writer(sample, str(out), variable_value_labels=meta.variable_value_labels)
        return out.read_bytes()


def make_ecu(period: Period, n: int, seed: int = 11) -> Path:
    import pyreadstat

    from lfspanel.fetch.ecu import find_zip

    src = find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = next(
            m
            for m in z.namelist()
            if "persona" in m.lower() and m.lower().endswith(".sav")
        )
    data = _sample_stata_like(
        src, member, pyreadstat.read_sav, pyreadstat.write_sav, n, seed, ".sav"
    )
    out = FIXTURES / "ecu" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"enemdu_persona_{period.year}_{period.roman}_sample.sav", data)
    return out


def make_per(period: Period, n: int, seed: int = 11) -> Path:
    import pyreadstat

    from lfspanel.fetch.per import find_zip

    src = find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".dta"))
    data = _sample_stata_like(
        src, member, pyreadstat.read_dta, pyreadstat.write_dta, n, seed, ".dta"
    )
    out = FIXTURES / "per" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Nacional EPEN Trim. sample.dta", data)
    return out


def make_zaf(period: Period, n: int, seed: int = 11) -> Path:
    """Sample QLFS rows; written back as Stata 118 with pandas (readstat rejects the
    original file's character set, so the reader uses pandas as well)."""
    import io

    from lfspanel.fetch.zaf import find_zip

    src = find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".dta"))
        reader = pd.io.stata.StataReader(
            io.BytesIO(z.read(member)), convert_categoricals=False
        )
        df = reader.read()
        labels = reader.value_labels()
        reader.close()
    sample = df.sample(min(n, len(df)), random_state=seed)
    buf = io.BytesIO()
    sample.to_stata(buf, write_index=False, version=118, value_labels=None)
    out = FIXTURES / "zaf" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"qlfs-{period.year}-q{period.quarter}-sample.dta", buf.getvalue())
    del labels
    return out


def make_geo(period: Period, n: int, seed: int = 11) -> Path:
    """Sample rows of the ECSTAT file for one quarter (kept as an annual-style zip)."""
    import pyreadstat

    from lfspanel.fetch.geo import find_zip, quarter_number

    src = find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = next(
            m for m in z.namelist() if m.lower().split("/")[-1].startswith("lfs_ecstat")
        )
    import tempfile

    with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "in.sav"
        path.write_bytes(z.read(member))
        df, meta = pyreadstat.read_sav(str(path))
        df = df[df["QuarterNo"] == quarter_number(period)]
        sample = df.sample(min(n, len(df)), random_state=seed)
        out_sav = Path(tmp) / "out.sav"
        pyreadstat.write_sav(
            sample, str(out_sav), variable_value_labels=meta.variable_value_labels
        )
        data = out_sav.read_bytes()
    out = FIXTURES / "geo" / f"Labour-Force-Survey-{period.year}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"SPSS_{period.year}_ENG/LFS_ECSTAT_ENG_{period.year}.sav", data)
    return out


def make_phl(period: Period, n: int, seed: int = 11) -> Path:
    """Sample rows of the PUF CSV (kept under its original member name)."""
    from lfspanel.fetch.phl import find_zip

    src = find_zip(period)
    with zipfile.ZipFile(src) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".csv"))
        t = pd.read_csv(
            z.open(member), dtype=str, keep_default_na=False, encoding="latin-1"
        )
    sample = t.sample(min(n, len(t)), random_state=seed)
    out = FIXTURES / "phl" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            member, sample.to_csv(index=False, lineterminator="\n").encode("latin-1")
        )
    return out


def make_nga(period: Period, n: int, seed: int = 11) -> Path:
    """Sample rows of an NLFS Stata file; written back as Stata 118 with pandas."""
    import io

    from lfspanel.fetch.nga import find_zip

    src = find_zip(period)
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            member = next(m for m in z.namelist() if m.lower().endswith("indiv.dta"))
            data = z.read(member)
    else:
        data = src.read_bytes()
    reader = pd.io.stata.StataReader(io.BytesIO(data), convert_categoricals=False)
    df = reader.read()
    reader.close()
    sample = df.sample(min(n, len(df)), random_state=seed)
    text_cols = [c for c in sample.columns if sample[c].dtype == object]
    sample = sample.drop(columns=[c for c in text_cols if c.endswith("ots")])
    out = FIXTURES / "nga" / f"nlfs_{period.year}q{period.quarter}_indiv.dta"
    out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_stata(out, write_index=False, version=118, value_labels=None)
    return out


def make_ind(period: Period, n: int, seed: int = 11) -> Path:
    """Sample one quarter of a PLFS Stata release (person + household members)."""
    import tempfile

    from lfspanel.fetch.ind import find_zip, release_for
    from lfspanel.read.ind import ALIASES, HH_ALIASES, quarter_label

    rel = release_for(period)
    src = find_zip(period)
    label = quarter_label(rel, period)
    qtr_col = ALIASES[rel.label].get("qtr", "qtr")
    hh_alias = HH_ALIASES.get(rel.label, {})
    with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as tmp:
        names = z.namelist()
        pmember = next(
            m for m in names if re.search(rel.person_member, Path(m).name, re.I)
        )
        hmember = next(m for m in names if re.search(rel.hh_member, Path(m).name, re.I))
        ppath = Path(tmp) / "p.dta"
        ppath.write_bytes(z.read(pmember))
        parts = []
        for chunk in pd.read_stata(
            ppath, chunksize=200_000, convert_categoricals=False
        ):
            parts.append(chunk[chunk[qtr_col].astype(str).str.strip() == label])
        persons = pd.concat(parts, ignore_index=True)
        sample = persons.sample(min(n, len(persons)), random_state=seed)
        hpath = Path(tmp) / "h.dta"
        hpath.write_bytes(z.read(hmember))
        hh = pd.read_stata(hpath, convert_categoricals=False)
        keys = ["mfsu", "sss", "ssu"]
        hh_cols = [hh_alias.get(k, k) for k in keys]
        p_cols = [ALIASES[rel.label].get(k, k) for k in keys]
        hh_key = hh[hh_cols].astype(str).agg("|".join, axis=1)
        p_key = sample[p_cols].astype(str).agg("|".join, axis=1)
        hh_sample = hh[hh_key.isin(set(p_key))]
        out = FIXTURES / "ind" / rel.label / src.name
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for member, frame in ((pmember, sample), (hmember, hh_sample)):
                buf = Path(tmp) / "out.dta"
                frame.to_stata(buf, write_index=False, version=118, value_labels=None)
                zout.writestr(member, buf.read_bytes())
    return out


def make_ury(period: Period, n: int, seed: int = 11) -> Path:
    """Sample rows of the first monthly file of the quarter (latin-1 CSV)."""
    from lfspanel.fetch.ury import month_file

    src = month_file(period, period.months[0])
    df = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="latin-1")
    sample = df.sample(min(n, len(df)), random_state=seed)
    out = FIXTURES / "ury" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out, index=False, encoding="latin-1")
    return out


def make_bol(period: Period, n: int, seed: int = 11) -> Path:
    """Sample one quarter of the ECE in the source's own layout.

    Quarters served by the pooled file give a semicolon CSV in the pooled
    file's layout restricted to the kept columns (decimal commas kept); later
    quarters give a zip with a Stata member of the kept columns, like INE's
    per-quarter zips.
    """
    import duckdb

    from lfspanel.fetch.bol import source_for
    from lfspanel.read.bol import keep_list, read_raw

    src = source_for(period)
    out_dir = FIXTURES / "bol"
    out_dir.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".csv":
        con = duckdb.connect()
        header = con.execute(
            f"select * from read_csv('{src}', delim=';', header=true, "
            "all_varchar=true) limit 0"
        ).df()
        cols = ", ".join(f'"{c}"' for c in keep_list() if c in header.columns)
        df = con.execute(
            f"select {cols} from read_csv('{src}', delim=';', header=true, "
            f"all_varchar=true, quote='\"') where gestion = '{period.year}' "
            f"and trimestre = '{period.quarter}'"
        ).df()
        sample = df.sample(min(n, len(df)), random_state=seed)
        out = out_dir / f"{src.name.replace('.utf8', '')}"
        sample.to_csv(out, index=False, sep=";", encoding="utf-8")
        return out
    raw = read_raw(period, path=src)
    sample = raw.sample(min(n, len(raw)), random_state=seed).drop(columns="source_file")
    for c in ("fact_trim", "fact_trim_act", "yprilab", "phrs"):
        sample[c] = pd.to_numeric(sample[c], errors="coerce")
    for c in keep_list():
        if c not in ("fact_trim", "fact_trim_act", "yprilab", "phrs"):
            sample[c] = sample[c].astype(str)
    out = out_dir / src.name
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dta = Path(tmp) / src.with_suffix(".dta").name
            sample.to_stata(dta, write_index=False, version=118)
            z.write(dta, dta.name)
    return out


BUILDERS = {
    "bra": make_bra, "mex": make_mex, "col": make_col,
    "arg": make_arg, "ecu": make_ecu, "per": make_per, "zaf": make_zaf, "geo": make_geo,
    "phl": make_phl, "nga": make_nga, "ind": make_ind, "ury": make_ury, "bol": make_bol,
}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", required=True)
    ap.add_argument("--period", required=True)
    ap.add_argument("--n", type=int, default=400)
    args = ap.parse_args()
    country = get_country(args.country)
    if country.key not in BUILDERS:
        raise SystemExit(f"No fixture builder for {country.key} yet")
    print(BUILDERS[country.key](Period(args.period), args.n))


if __name__ == "__main__":
    main()
