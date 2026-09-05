import pandas as pd

from lfspanel.crosswalks import (
    isco08_codes_by_level,
    isco08_unit_groups,
    isco_parent,
    load_crosswalk,
    map_isco_codes,
)


def test_isco_structure_counts():
    by_level = isco08_codes_by_level()
    assert len(by_level[1]) == 10
    assert len(by_level[2]) == 43
    assert len(by_level[3]) == 130
    assert len(isco08_unit_groups()) == 436
    df = load_crosswalk("isco08_structure")
    assert df["code"].str.len().eq(4).all()
    assert not df.duplicated(["code", "level"]).any()


def test_map_isco_codes_depth():
    codes = pd.Series(["2512", "6220", "6225", "0000", "0412", "9999", "", None, "13"])
    isco, digits = map_isco_codes(codes)
    # 0412 and 9999 have no valid minor or sub-major parent, so fall to the major group
    assert isco.tolist()[:6] == ["2512", "6220", "6220", "0000", "0000", "9000"]
    assert digits.tolist()[:6] == [4, 3, 3, 1, 1, 1]
    assert pd.isna(isco.iloc[6]) and pd.isna(isco.iloc[7])
    assert isco.iloc[8] == "1300" and digits.iloc[8] == 2


def test_isco_parent():
    s = pd.Series(["2512", "6221"])
    assert isco_parent(s, 2).tolist() == ["2500", "6200"]
