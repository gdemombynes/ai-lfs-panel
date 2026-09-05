"""Parquet partitions and DuckDB views over the harmonized panel."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from lfspanel.config import DUCKDB_PATH, HARMONIZED
from lfspanel.schema import COLUMNS


def partition_path(source: str, ccc: str, period: str, root: Path = HARMONIZED) -> Path:
    return (
        root
        / f"source={source}"
        / f"countrycode={ccc}"
        / f"period={period}"
        / "data.parquet"
    )


def write_partition(df: pd.DataFrame, root: Path = HARMONIZED) -> Path:
    """Write one harmonized country-period frame atomically as Parquet."""
    for col in ("source", "countrycode", "period"):
        if df[col].nunique() != 1:
            raise ValueError(f"{col} must be constant within a partition")
    source, ccc, period = (
        str(df[c].iloc[0]) for c in ("source", "countrycode", "period")
    )
    dest = partition_path(source, ccc, period, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df[COLUMNS], preserve_index=False)
    fd, tmp = tempfile.mkstemp(prefix="data.", suffix=".parquet.part", dir=dest.parent)
    os.close(fd)
    pq.write_table(table, tmp, compression="zstd", use_dictionary=True)
    os.replace(tmp, dest)
    return dest


def read_partition(path: Path) -> pd.DataFrame:
    """Read one partition file; partition keys are stored in the file itself."""
    return pq.read_table(path, partitioning=None).to_pandas(types_mapper=_types_mapper)


def _types_mapper(arrow_type):
    mapping = {
        pa.int8(): pd.Int8Dtype(),
        pa.int16(): pd.Int16Dtype(),
        pa.int32(): pd.Int32Dtype(),
        pa.int64(): pd.Int64Dtype(),
        pa.string(): pd.StringDtype(),
        pa.large_string(): pd.StringDtype(),
    }
    return mapping.get(arrow_type)


def duckdb_connect(
    db_path: Path = DUCKDB_PATH, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path), read_only=read_only)


VIEW_SQL = """
CREATE OR REPLACE VIEW harmonized AS
SELECT * FROM read_parquet('{glob}', hive_partitioning = false, union_by_name = true);

CREATE OR REPLACE VIEW employed AS
SELECT *,
       CASE WHEN occup_isco_digits >= 1 THEN substr(occup_isco, 1, 1) END AS isco1,
       CASE WHEN occup_isco_digits >= 2 THEN substr(occup_isco, 1, 2) END AS isco2,
       CASE WHEN occup_isco_digits >= 3 THEN substr(occup_isco, 1, 3) END AS isco3,
       CASE WHEN age BETWEEN 15 AND 21 THEN '15-21'
            WHEN age BETWEEN 22 AND 25 THEN '22-25'
            WHEN age BETWEEN 26 AND 29 THEN '26-29'
            WHEN age BETWEEN 30 AND 49 THEN '30-49'
            WHEN age >= 50 THEN '50+' END AS age_group,
       age BETWEEN 18 AND 29 AS young
FROM harmonized
WHERE lstatus = 1;
"""


def build_views(db_path: Path = DUCKDB_PATH, root: Path = HARMONIZED) -> None:
    """(Re)create the ``harmonized`` and ``employed`` views over all partitions."""
    glob = str(root / "source=*" / "countrycode=*" / "period=*" / "data.parquet")
    con = duckdb_connect(db_path)
    try:
        for stmt in VIEW_SQL.format(glob=glob).split(";"):
            if stmt.strip():
                con.execute(stmt)
    finally:
        con.close()


def panel_summary(
    db_path: Path = DUCKDB_PATH, where: Optional[str] = None
) -> pd.DataFrame:
    """Rows and weighted population per source / country / period."""
    con = duckdb_connect(db_path, read_only=True)
    try:
        sql = (
            "SELECT source, countrycode, period, count(*) AS n, sum(weight) AS pop "
            "FROM harmonized"
            + (f" WHERE {where}" if where else "")
            + " GROUP BY 1, 2, 3 ORDER BY 2, 3, 1"
        )
        return con.execute(sql).df()
    finally:
        con.close()
