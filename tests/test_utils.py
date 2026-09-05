"""Tests for analysis.utils."""

import pandas as pd
import pytest

from analysis.utils import load_data, save_data


def test_save_then_load_round_trips(tmp_path):
    df = pd.DataFrame({"x": [1, 2, 3], "label": ["a", "b", "c"]})
    target = tmp_path / "nested" / "data.csv"

    save_data(df, target)
    loaded = load_data(target)

    pd.testing.assert_frame_equal(df, loaded)


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(tmp_path / "does_not_exist.csv")
