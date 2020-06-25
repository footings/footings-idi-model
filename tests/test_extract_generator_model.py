import os

import pandas as pd

from idi_model import extract_generator_model

volume_tbl = pd.read_csv(os.path.join("tests", "data", "volume-tbl.csv"))


def test_disabled_life_extract():
    extract = extract_generator_model(
        n=100,
        volume_tbl=volume_tbl,
        as_of_dt=pd.Timestamp("2020-03-31"),
        extract_type="disabled-lives",
        seed=1,
    ).run()
    extract.to_csv("disabled-extract.csv", index=False)
    assert isinstance(extract, pd.DataFrame)
    assert extract.shape[0] == 100


def test_active_life_extract():
    extract = extract_generator_model(
        n=100,
        volume_tbl=volume_tbl,
        as_of_dt=pd.Timestamp("2020-03-31"),
        extract_type="active-lives",
        seed=1,
    ).run()
    extract.to_csv("active-extract.csv", index=False)
    assert isinstance(extract, pd.DataFrame)
    assert extract.shape[0] == 100
