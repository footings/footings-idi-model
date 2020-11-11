import os

import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from footings_idi_model.utils import GenerateALRExtracts


def test_generate_active_extract():
    base_test, rider_test = GenerateALRExtracts(
        n=100,
        volume_tbl=pd.read_csv(os.path.join("tests", "utils", "volume-tbl.csv")),
        as_of_dt=pd.Timestamp("2020-03-31"),
        rop_rider_percent=0.5,
        seed=1,
    ).run()
    rider_test["VALUE"] = rider_test["VALUE"].astype(str)
    base_expected = pd.read_csv(
        os.path.join("tests", "utils", "expected-extract-base-alr.csv"),
        parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"],
    )
    assert_frame_equal(base_test, base_expected)
    rider_expected = pd.read_csv(
        os.path.join("tests", "utils", "expected-extract-rider-alr.csv")
    )
    assert_frame_equal(rider_test, rider_expected)
