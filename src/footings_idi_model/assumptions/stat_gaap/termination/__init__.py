import os
import json
from functools import lru_cache

import numpy as np
import pandas as pd

from footings.model_tools import once

directory, filename = os.path.split(__file__)


@once
def get_contract_modifier():
    """Get contract modifier"""
    file = os.path.join(directory, "2013-idi-contract-modifier.csv")
    dtypes = {"IDI_CONTRACT": "category"}
    return pd.read_csv(file, dtype=dtypes)


@once
def get_benefit_period_modifier():
    """Get benefit period modifier"""
    file = os.path.join(directory, "2013-idi-benefit-period-modifier.csv")
    dtypes = {"IDI_BENEFIT_PERIOD": "category", "COLA_FLAG": "category"}
    return pd.read_csv(file, dtype=dtypes)


@once
def get_diagnosis_modifier():
    """Get diagnosis modifier"""
    file = os.path.join(directory, "2013-idi-diagnosis-modifier.csv")
    dtypes = {"IDI_DIAGNOSIS_GRP": "category"}
    return pd.read_csv(file, dtype=dtypes)


@once
def get_cause_modifier():
    """Get cause modifier"""
    file = os.path.join(directory, "2013-idi-cause-modifier.csv")
    dtypes = {"IDI_CONTRACT": "category", "GENDER": "category"}
    return pd.read_csv(file, dtype=dtypes)


@once
def get_select_ctr():
    """Get select CTR"""
    file = os.path.join(directory, "2013-idi-base-ctr-select.csv")
    dtypes = {
        "IDI_OCCUPATION_CLASS": "category",
        "GENDER": "category",
        "PERIOD": "category",
    }
    return pd.read_csv(file, dtype=dtypes)


@once
def get_ultimate_ctr():
    """Get ultimate CTR"""
    file = os.path.join(directory, "2013-idi-base-ctr-ultimate.csv")
    dtypes = {"IDI_OCCUPATION_CLASS": "category", "GENDER": "category"}
    return pd.read_csv(file, dtype=dtypes)


@once
def get_margin():
    """Get termination margin"""
    file = os.path.join(directory, "margin.json")
    with open(file, "r") as f:
        margin = json.load(f)
    return margin


def margin_to_table_select(margin):
    """Transform margin to table"""
    margin = [1 - margin["DURATION_1"]] + [
        1 - margin["DURATION_2+"] for i in range(1, 100)
    ]
    tbl = pd.DataFrame({"DURATION_YEAR": range(1, 101), "MARGIN_SELECT": margin})
    return tbl


@lru_cache(maxsize=None)
def make_select_rates(
    idi_benefit_period,
    idi_contract,
    idi_diagnosis_grp,
    idi_occupation_class,
    gender,
    elimination_period,
    age_incurred,
    cola_flag,
    mode,
):
    """ """

    def _make_query(*args):
        return " and ".join(args)

    def _specify_mode(tbl, mode):
        cols = ["IDI_CONTRACT", "GENDER", "DURATION_YEAR", "CAUSE_MODIFIER"]
        if mode == "DLR":
            tbl = tbl.rename(columns={"CAUSE_MODIFIER_DLR": "CAUSE_MODIFIER"})
            return tbl[cols]
        elif mode == "ALR":
            tbl = tbl.rename(columns={"CAUSE_MODIFIER_ALR": "CAUSE_MODIFIER"})
            return tbl[cols]
        else:
            raise ValueError(f"The mode [{mode}] is not recognized.")

    bp_query = "IDI_BENEFIT_PERIOD==@idi_benefit_period"
    ct_query = "IDI_CONTRACT==@idi_contract"
    dg_query = "IDI_DIAGNOSIS_GRP==@idi_diagnosis_grp"
    oc_query = "IDI_OCCUPATION_CLASS==@idi_occupation_class"
    gd_query = "GENDER==@gender"
    ep_query = "ELIMINATION_PERIOD==@elimination_period"
    ai_query = "AGE_INCURRED==@age_incurred"
    ca_query = "COLA_FLAG==@cola_flag"

    select_tbl = get_select_ctr().query(
        _make_query(oc_query, gd_query, ep_query, ai_query)
    )
    bp_tbl = get_benefit_period_modifier().query(_make_query(bp_query, ca_query))
    contract_tbl = get_contract_modifier().query(ct_query)
    cause_tbl = (
        get_cause_modifier()
        .query(_make_query(ct_query, gd_query))
        .pipe(_specify_mode, mode)
    )
    diagnosis_tbl = get_diagnosis_modifier().query(dg_query)
    margin_tbl = margin_to_table_select(get_margin())

    col_order = [
        "DURATION_YEAR",
        "DURATION_MONTH",
        "PERIOD",
        "SELECT_CTR",
        "BENEFIT_PERIOD_MODIFIER",
        "CONTRACT_MODIFIER",
        "DIAGNOSIS_MODIFIER",
        "CAUSE_MODIFIER",
        "MARGIN_SELECT",
        "FINAL_SELECT_CTR",
    ]

    rate_tbl = (
        select_tbl.merge(bp_tbl, how="left", on=["DURATION_YEAR"])
        .merge(contract_tbl, how="left", on=["DURATION_YEAR"])
        .merge(diagnosis_tbl, how="left", on=["DURATION_YEAR"])
        .merge(cause_tbl, how="left", on=["DURATION_YEAR", "GENDER", "IDI_CONTRACT"])
        .merge(margin_tbl, how="left", on=["DURATION_YEAR"])
        .assign(
            FINAL_SELECT_CTR=lambda df: df.SELECT_CTR
            * df.BENEFIT_PERIOD_MODIFIER
            * df.CONTRACT_MODIFIER
            * df.CAUSE_MODIFIER
            * df.DIAGNOSIS_MODIFIER
            * df.MARGIN_SELECT,
        )
    )[col_order]
    return rate_tbl


@lru_cache(maxsize=None)
def make_ultimate_rates(idi_occupation_class, gender):
    """ """
    query = "IDI_OCCUPATION_CLASS==@idi_occupation_class and GENDER==@gender"
    ultimate_tbl = get_ultimate_ctr().query(query)
    margin = get_margin()["DURATION_2+"]
    rate_tbl = ultimate_tbl.assign(
        MARGIN_ULTIMATE=1 - margin,
        FINAL_ULTIMATE_CTR=lambda df: df.ULTIMATE_CTR * df.MARGIN_ULTIMATE,
    )
    return rate_tbl[
        ["AGE_ATTAINED", "ULTIMATE_CTR", "MARGIN_ULTIMATE", "FINAL_ULTIMATE_CTR"]
    ]


def _stat_gaap_ctr(
    frame,
    idi_benefit_period,
    idi_contract,
    idi_diagnosis_grp,
    idi_occupation_class,
    gender,
    elimination_period,
    age_incurred,
    cola_percent,
    mode,
):
    cola_flag = "N" if cola_percent == 0 else "Y"
    select_tbl = make_select_rates(
        idi_benefit_period=idi_benefit_period,
        idi_contract=idi_contract,
        idi_diagnosis_grp=idi_diagnosis_grp,
        idi_occupation_class=idi_occupation_class,
        gender=gender,
        elimination_period=elimination_period,
        age_incurred=age_incurred,
        cola_flag=cola_flag,
        mode=mode,
    )
    ultimate_tbl = make_ultimate_rates(
        idi_occupation_class=idi_occupation_class, gender=gender
    )
    tbl = (
        frame[["AGE_ATTAINED", "DURATION_YEAR", "DURATION_MONTH"]]
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
