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
def get_withdraw_table(table_nm):
    """Get withdraw rates."""
    file = WITHDRAW_TABLES.get(table_nm, None)
    if file is None:
        raise ValueError(f"The table [{table_nm}] is not known. See documentation.")
    return pd.read_csv(file)
