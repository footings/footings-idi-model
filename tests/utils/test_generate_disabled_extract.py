import os

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from footings_idi_model.utils import GenerateDLRExtract


def test_generate_disabled_extract():
    test = GenerateDLRExtract(
        n=100,
        volume_tbl=pd.read_csv(os.path.join("tests", "utils", "volume-tbl.csv")),
        as_of_dt=pd.Timestamp("2020-03-31"),
        seed=1,
    ).run()
    expected_file = os.path.join("tests", "utils", "expected-extract-dlr.csv")
    expected = pd.read_csv(
        expected_file, parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"]
    )
    assert_frame_equal(test, expected)
