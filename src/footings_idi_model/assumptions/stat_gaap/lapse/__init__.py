import os

import pandas as pd
from footings.utils import once

directory, filename = os.path.split(__file__)


@once
def load_lapse_file():
    return pd.read_csv(os.path.join(directory, "lapse-rate-table.csv"))


def get_lapse_rates(age_issued: int, modifier_lapse: float):
    return (
        load_lapse_file()
        .query("ISSUE_AGE_MIN <= @age_issue <= ISSUE_AGE_MAX")
        .assign(
            MODIFIER_LAPSE=modifier_lapse,
            LAPSE_RATE=lambda df: df.BASE_LAPSE_RATE * df.MODIFIER_LAPSE,
        )
    )
