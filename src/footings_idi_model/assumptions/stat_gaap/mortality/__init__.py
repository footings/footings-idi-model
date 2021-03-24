import os
from functools import lru_cache

import pandas as pd

directory, filename = os.path.split(__file__)

WITHDRAW_TABLES = {
    "01CSO": os.path.join(directory, "01CSO.csv"),
    "17CSO": os.path.join(directory, "17CSO.csv"),
    "58CSO": os.path.join(directory, "58CSO.csv"),
    "80CSO": os.path.join(directory, "80CSO.csv"),
}


@lru_cache(maxsize=4)
def get_mortality_rates(table_name: str, gender: str, modifier_mortality: float):
    """Get mortality rates."""
    file = WITHDRAW_TABLES.get(table_name, None)
    if file is None:
        raise ValueError(f"The table [{table_name}] is not known. See documentation.")
    return (
        pd.read_csv(file)
        .rename(columns={"MORTALITY_RATE": "BASE_MORTALITY_RATE"})
        .query("GENDER==@gender")
        .assign(
            MODIFIER_MORTALITY=modifier_mortality,
            MORTALITY_RATE=lambda df: df.BASE_MORTALITY_RATE * df.MODIFIER_MORTALITY,
        )
    )
