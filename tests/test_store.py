import duckdb

from lfspanel.store import build_views, partition_path, read_partition, write_partition


def test_write_read_partition_and_views(tmp_path, harmonized_frame):
    root = tmp_path / "harmonized"
    dest = write_partition(harmonized_frame, root=root)
    assert dest == partition_path("own", "BRA", "2025Q1", root)
    back = read_partition(dest)
    assert len(back) == len(harmonized_frame)
    assert str(back["lstatus"].dtype) == "Int8"

    db = tmp_path / "panel.duckdb"
    build_views(db, root)
    con = duckdb.connect(str(db), read_only=True)
    n_emp = con.execute("select count(*) from employed").fetchone()[0]
    isco1 = con.execute("select isco1 from employed order by isco1").fetchall()
    con.close()
    assert n_emp == 2
    assert isco1 == [("0",), ("2",)]
