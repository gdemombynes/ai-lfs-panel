"""Paths, secrets and the country registry."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = Path(os.environ.get("LFSPANEL_DATA_DIR", ROOT / "data"))
RAW = DATA / "raw"
EXTERNAL = DATA / "external"
PROCESSED = DATA / "processed"
HARMONIZED = PROCESSED / "harmonized"
MANIFEST = RAW / "manifest.csv"
DUCKDB_PATH = PROCESSED / "panel.duckdb"
OUTPUT = ROOT / "output"

HARMONIZE_VERSION = "0.1.0"


def secret(name: str) -> str:
    """Return an environment secret or raise with a pointer to .env."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set; add it to {ROOT / '.env'}")
    return value


@dataclass(frozen=True)
class Country:
    """Static facts about one survey in the panel."""

    ccc: str  # ISO3, upper case
    survey: str  # short survey slug used in folder names
    survey_name: str
    agency: str
    freq: str  # "Q" quarterly files, "M" monthly files
    minlaborage: int
    isco_digits: int  # reliable ISCO-08 digits after harmonization
    isic_digits: int  # reliable ISIC Rev.4 digits after harmonization
    access: str  # open | registration | api | manual
    first_period: str

    @property
    def key(self) -> str:
        return self.ccc.lower()

    @property
    def raw_dir(self) -> Path:
        return RAW / self.key / self.survey


COUNTRIES = {
    "bra": Country(
        ccc="BRA",
        survey="pnadc",
        survey_name="PNAD Contínua (trimestral)",
        agency="IBGE",
        freq="Q",
        minlaborage=14,
        isco_digits=4,
        isic_digits=2,
        access="open",
        first_period="2022Q1",
    ),
    "mex": Country(
        ccc="MEX",
        survey="enoe",
        survey_name="Encuesta Nacional de Ocupación y Empleo",
        agency="INEGI",
        freq="Q",
        minlaborage=15,
        isco_digits=3,
        isic_digits=2,
        access="open",
        first_period="2022Q1",
    ),
    "col": Country(
        ccc="COL",
        survey="geih",
        survey_name="Gran Encuesta Integrada de Hogares",
        agency="DANE",
        freq="M",
        minlaborage=15,
        isco_digits=4,
        isic_digits=4,
        access="open",
        first_period="2022Q1",
    ),
    "arg": Country(
        ccc="ARG",
        survey="eph",
        survey_name="Encuesta Permanente de Hogares",
        agency="INDEC",
        freq="Q",
        minlaborage=10,
        isco_digits=2,
        isic_digits=2,
        access="open",
        first_period="2022Q1",
    ),
    "ecu": Country(
        ccc="ECU",
        survey="enemdu",
        survey_name="ENEMDU trimestral",
        agency="INEC",
        freq="Q",
        minlaborage=15,
        isco_digits=4,
        isic_digits=4,
        access="open",
        first_period="2022Q1",
    ),
    "per": Country(
        ccc="PER",
        survey="enaho",
        survey_name="ENAHO trimestral, módulo 500",
        agency="INEI",
        freq="Q",
        minlaborage=14,
        isco_digits=4,
        isic_digits=4,
        access="open",
        first_period="2022Q1",
    ),
    "zaf": Country(
        ccc="ZAF",
        survey="qlfs",
        survey_name="Quarterly Labour Force Survey",
        agency="Stats SA",
        freq="Q",
        minlaborage=15,
        isco_digits=3,
        isic_digits=2,
        access="manual",
        first_period="2022Q1",
    ),
    "ind": Country(
        ccc="IND",
        survey="plfs",
        survey_name="Periodic Labour Force Survey",
        agency="MoSPI / NSO",
        freq="Q",
        minlaborage=15,
        isco_digits=3,
        isic_digits=4,
        access="api",
        first_period="2022Q1",
    ),
}


def get_country(key: str) -> Country:
    """Look up a country by lower-case ISO3 key, e.g. ``"bra"``."""
    try:
        return COUNTRIES[key.lower()]
    except KeyError as exc:
        raise KeyError(f"Unknown country {key!r}; known: {sorted(COUNTRIES)}") from exc
