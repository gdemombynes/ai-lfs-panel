import pytest

from lfspanel.periods import Period, parse_periods, period_range


def test_quarter_parsing_and_properties():
    p = Period("2025q1")
    assert (p.year, p.quarter, p.month) == (2025, 1, None)
    assert str(p) == "2025Q1"
    assert p.ibge_code == "012025"
    assert p.roman == "I"
    assert p.months == [1, 2, 3]
    assert not p.is_month


def test_month_knows_its_quarter():
    m = Period("2023M11")
    assert m.quarter == 4
    assert m.quarter_period == Period("2023Q4")
    assert str(m) == "2023M11"
    assert m.months == [11]


def test_ordering_and_next():
    assert Period("2022Q4") < Period("2023Q1")
    assert Period("2022Q4").next() == Period("2023Q1")
    assert Period("2023M12").next() == Period("2024M01")


def test_period_range_and_parse():
    assert [str(p) for p in period_range("2022Q3", "2023Q1")] == [
        "2022Q3",
        "2022Q4",
        "2023Q1",
    ]
    assert [str(p) for p in parse_periods("2025Q1,2025Q3")] == ["2025Q1", "2025Q3"]
    assert len(parse_periods("2022Q1:2026Q2")) == 18


@pytest.mark.parametrize("bad", ["2023Q5", "2023M13", "2023", "Q12023"])
def test_bad_periods_raise(bad):
    with pytest.raises(ValueError):
        Period(bad)


def test_mixed_kinds_raise():
    with pytest.raises(ValueError):
        list(period_range("2023Q1", "2023M06"))
