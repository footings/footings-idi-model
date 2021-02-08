from footings.utils import dispatch_function

from .stat_gaap.withdraw import get_withdraw_table


@dispatch_function(key_parameters=("assumption_set",))
def get_withdraw_rates(assumption_set, table_name, gender):
    """ """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@get_withdraw_rates.register(assumption_set="stat")
def _(table_name, gender):
    return get_withdraw_table(table_name, gender)


@get_withdraw_rates.register(assumption_set="gaap")
def _(table_name, gender):
    return get_withdraw_table(table_name, gender)


@get_withdraw_rates.register(assumption_set="best-estimate")
def _(table_name):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")
