"""Prepare lapse assumptions"""

import os
from functools import lru_cache

import pandas as pd
import numpy as np

directory, filename = os.path.split(__file__)


def get_age_band():
    """Get age band"""
    bands = [
        np.repeat("20-25", 6),
        np.repeat("26-30", 5),
        np.repeat("31-35", 5),
        np.repeat("36-40", 5),
        np.repeat("41-45", 5),
        np.repeat("46-50", 5),
        np.repeat("51-55", 5),
        np.repeat("56-60", 5),
        np.repeat("61+", 10),
    ]
    return pd.DataFrame({"AGE_BAND": np.concatenate(bands), "AGE_ISSUED": range(20, 71)})


@lru_cache(maxsize=2)
def _get_lapses(file):
    return pd.read_csv(file)


def get_lapses(table_nm):
    """Get benefit period modifier"""
    return _get_lapses(os.path.join(directory, f"{table_nm}.csv"))
