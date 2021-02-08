"""Prepare interest assumptions"""

import json
import os
from functools import lru_cache

import pandas as pd

directory, filename = os.path.split(__file__)

interest_file = os.path.join(directory, "interest.json")


@lru_cache(maxsize=1)
def _get_interest_rate():
    """Get termination margin"""

    with open(interest_file, "r") as f:
        interest_records = json.load(f)
    interest_dict = {}
    for record in interest_records:
        years = range(record["min_disable_year"], record["max_disable_year"] + 1)
        interest_dict.update([(year, record["interest"]) for year in years])
    return interest_dict


def get_interest_rate(incurred_dt: pd.Timestamp):
    """Get the valuation interest rate based of the incurred date."""
    return _get_interest_rate()[incurred_dt.year]
