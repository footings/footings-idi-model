import numpy as np
import pandas as pd
from footings import dispatch_function

from .stat_gaap.withdraw import get_withdraw_table


@dispatch_function(key_parameters=("assumption_set",))
def get_withdraw_rates(assumption_set, table_name):
    """ """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@get_withdraw_rates.register(assumption_set="stat")
def _(mode, table_name):
    return get_withdraw_table(table_name)


@get_withdraw_rates.register(assumption_set="gaap")
def _(mode, table_name):
    return get_withdraw_table(table_name)


@get_withdraw_rates.register(assumption_set="best-estimate")
def _(mode, table_name):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")
