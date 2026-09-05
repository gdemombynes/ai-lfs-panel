"""Read PNAD Contínua fixed-width microdata using IBGE's SAS input layout."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from lfspanel.fetch.bra import find_zip
from lfspanel.periods import Period

LAYOUT_RESOURCE = "layouts/input_PNADC_trimestral_20221031.sas"
KEEP_RESOURCE = "keep_lists/bra.txt"
_LINE = re.compile(r"^@(\d+)\s+(\w+)\s+(\$?)(\d+)\.", re.M)


@dataclass(frozen=True)
class Field:
    name: str
    start: int  # 0-based
    width: int
    is_char: bool

    @property
    def end(self) -> int:
        return self.start + self.width


def _resource_text(name: str) -> str:
    return (files("lfspanel") / "resources" / name).read_text(encoding="latin-1")


def parse_sas_layout(text: Optional[str] = None) -> List[Field]:
    """Parse ``@pos NAME $len.`` lines from IBGE's SAS input program."""
    text = text if text is not None else _resource_text(LAYOUT_RESOURCE)
    fields = [
        Field(
            name=m.group(2),
            start=int(m.group(1)) - 1,
            width=int(m.group(4)),
            is_char=bool(m.group(3)),
        )
        for m in _LINE.finditer(text)
    ]
    if not fields:
        raise ValueError("No fields parsed from SAS layout")
    return fields


def keep_list() -> List[str]:
    lines = _resource_text(KEEP_RESOURCE).splitlines()
    return [ln.split("#", 1)[0].strip() for ln in lines if ln.split("#", 1)[0].strip()]


def _read_fwf(
    handle, fields: Iterable[Field], nrows: Optional[int] = None
) -> pd.DataFrame:
    fields = list(fields)
    df = pd.read_fwf(
        handle,
        colspecs=[(f.start, f.end) for f in fields],
        names=[f.name for f in fields],
        dtype=str,
        header=None,
        nrows=nrows,
        keep_default_na=False,
        na_values=[""],
        encoding="latin-1",
    )
    for f in fields:
        if not f.is_char:
            df[f.name] = pd.to_numeric(df[f.name], errors="coerce")
        else:
            df[f.name] = df[f.name].replace("", pd.NA).astype("string")
    return df


def read_raw(
    period: Period,
    keep: Optional[List[str]] = None,
    nrows: Optional[int] = None,
    path: Optional[Path] = None,
) -> pd.DataFrame:
    """Read one quarter's microdata (from the zip) keeping only ``keep`` fields."""
    keep = keep or keep_list()
    layout = {f.name: f for f in parse_sas_layout()}
    missing = [k for k in keep if k not in layout]
    if missing:
        raise KeyError(f"Keep list names not in layout: {missing}")
    fields = [layout[k] for k in keep]
    src = path or find_zip(period)
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            member = next(n for n in z.namelist() if n.lower().endswith(".txt"))
            with z.open(member) as fh:
                df = _read_fwf(fh, fields, nrows=nrows)
        df["source_file"] = f"{src.name}:{member}"
    else:
        df = _read_fwf(src, fields, nrows=nrows)
        df["source_file"] = src.name
    return df
