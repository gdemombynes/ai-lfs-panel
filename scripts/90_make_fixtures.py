"""Write small raw extracts under tests/fixtures/ for unit tests.

    python scripts/90_make_fixtures.py --country bra --period 2025Q1 --n 60
    python scripts/90_make_fixtures.py --country mex --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country col --period 2025M01 --n 500
    python scripts/90_make_fixtures.py --country arg --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country ecu --period 2025Q1 --n 400
    python scripts/90_make_fixtures.py --country per --period 2025Q1 --n 400

Fixtures are random samples of public microdata rows in the original file
layout, so reader and harmonizer tests exercise the real formats.
"""

from __future__ import annotations

import argparse
import random
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


BUILDERS = {
    "bra": make_bra, "mex": make_mex, "col": make_col,
    "arg": make_arg, "ecu": make_ecu, "per": make_per,
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
