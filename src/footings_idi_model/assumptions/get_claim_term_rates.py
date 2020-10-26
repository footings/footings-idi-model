import numpy as np
import pandas as pd
from footings import dispatch_function
from .stat_gaap.termination import make_select_rates, make_ultimate_rates


def _stat_gaap_ctr(mode, model_object):
    cola_flag = "N" if model_object.cola_percent == 0 else "Y"
    select_tbl = make_select_rates(
        idi_benefit_period=model_object.idi_benefit_period,
        idi_contract=model_object.idi_contract,
        idi_diagnosis_grp=model_object.idi_diagnosis_grp,
        idi_occupation_class=model_object.idi_occupation_class,
        gender=model_object.gender,
        elimination_period=model_object.elimination_period,
        age_incurred=model_object.age_incurred,
        cola_flag=cola_flag,
        mode=model_object.mode,
    )
    ultimate_tbl = make_ultimate_rates(
        idi_occupation_class=model_object.idi_occupation_class, gender=model_object.gender
    )
    tbl = (
        model_object.frame[["AGE_ATTAINED", "DURATION_YEAR", "DURATION_MONTH"]]
        .merge(select_tbl, how="left", on=["DURATION_YEAR", "DURATION_MONTH"])
        .merge(ultimate_tbl, how="left", on=["AGE_ATTAINED"])
    )
    condlist = [
        tbl.PERIOD == "M",
        tbl.PERIOD == "Y",
        tbl.PERIOD.isna(),
    ]
    choicelist = [
        tbl.FINAL_SELECT_CTR,
        1 - (1 - tbl.FINAL_SELECT_CTR) ** (1 / 12),
        1 - (1 - tbl.FINAL_ULTIMATE_CTR) ** (1 / 12),
    ]
    tbl["CTR"] = np.select(condlist, choicelist)
    return tbl


@dispatch_function(key_parameters=("assumption_set",))
def get_ctr_table(assumption_set, mode, model_object):
    """Calculate claim termination rate (CTR) which varies by assumption_set (e.g., GAAP) 
    and mode (i.e., ALR vs DLR).

    The CTR utilizes the select and ultimate tables required by the 2013 IDI Valuation Standard,
    as well as the required modifiers. The difference between running STAT vs GAAP is the use of
    margin. STAT includes it and GAAP does not.

    Parameters
    ----------
    assumption_set : str
    mode : str
    frame : pd.DataFrame
    
    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an extra column for CTR.
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@get_ctr_table.register(assumption_set="gaap")
def _(mode, model_object):
    return _stat_gaap_ctr(mode, model_object)


@get_ctr_table.register(assumption_set="stat")
def _(mode, model_object):
    return _stat_gaap_ctr(mode, model_object)


@get_ctr_table.register(assumption_set="best-estimate")
def _(mode, model_object):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")
