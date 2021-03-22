import json
import os

import numpy as np
import pandas as pd
from footings.utils import once

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
def get_base_select_ctr():
    """Get select CTR"""
    file = os.path.join(directory, "2013-idi-base-ctr-select.csv")
    dtypes = {
        "IDI_OCCUPATION_CLASS": "category",
        "GENDER": "category",
        "PERIOD": "category",
    }
    return pd.read_csv(file, dtype=dtypes)


@once
def get_base_ultimate_ctr():
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


def get_ctr_select(
    idi_benefit_period: str,
    idi_contract: str,
    idi_diagnosis_grp: str,
    idi_occupation_class: str,
    gender: str,
    elimination_period: int,
    age_incurred: int,
    cola_percent: str,
    model_mode: str,
):
    """Generate ctr select rates."""

    def _make_query(*args):
        return " and ".join(args)

    def _specify_model_mode(tbl, model_mode):
        cols = ["IDI_CONTRACT", "GENDER", "DURATION_YEAR", "CAUSE_MODIFIER"]
        if model_mode[:3] == "DLR":
            tbl = tbl.rename(columns={"CAUSE_MODIFIER_DLR": "CAUSE_MODIFIER"})
            return tbl[cols]
        elif model_mode[:3] == "ALR":
            tbl = tbl.rename(columns={"CAUSE_MODIFIER_ALR": "CAUSE_MODIFIER"})
            return tbl[cols]
        else:
            raise ValueError(f"The model_mode [{model_mode}] is not recognized.")

    cola_flag = "N" if cola_percent == 0 else "Y"

    bp_query = "IDI_BENEFIT_PERIOD==@idi_benefit_period"
    ct_query = "IDI_CONTRACT==@idi_contract"
    dg_query = "IDI_DIAGNOSIS_GRP==@idi_diagnosis_grp"
    oc_query = "IDI_OCCUPATION_CLASS==@idi_occupation_class"
    gd_query = "GENDER==@gender"
    ep_query = "ELIMINATION_PERIOD==@elimination_period"
    ai_query = "AGE_INCURRED==@age_incurred"
    ca_query = "COLA_FLAG==@cola_flag"

    select_tbl = get_base_select_ctr().query(
        _make_query(oc_query, gd_query, ep_query, ai_query)
    )
    bp_tbl = get_benefit_period_modifier().query(_make_query(bp_query, ca_query))
    contract_tbl = get_contract_modifier().query(ct_query)
    cause_tbl = (
        get_cause_modifier()
        .query(_make_query(ct_query, gd_query))
        .pipe(_specify_model_mode, model_mode)
    )
    diagnosis_tbl = get_diagnosis_modifier().query(dg_query)
    margin_tbl = margin_to_table_select(get_margin())

    col_order = [
        "DURATION_YEAR",
        "DURATION_MONTH",
        "PERIOD",
        "BASE_SELECT_CTR",
        "BENEFIT_PERIOD_MODIFIER",
        "CONTRACT_MODIFIER",
        "DIAGNOSIS_MODIFIER",
        "CAUSE_MODIFIER",
        "MARGIN_SELECT",
        "SELECT_CTR",
    ]

    rate_tbl = (
        select_tbl.merge(bp_tbl, how="left", on=["DURATION_YEAR"])
        .merge(contract_tbl, how="left", on=["DURATION_YEAR"])
        .merge(diagnosis_tbl, how="left", on=["DURATION_YEAR"])
        .merge(cause_tbl, how="left", on=["DURATION_YEAR", "GENDER", "IDI_CONTRACT"])
        .merge(margin_tbl, how="left", on=["DURATION_YEAR"])
        .assign(
            SELECT_CTR=lambda df: df.BASE_SELECT_CTR
            * df.BENEFIT_PERIOD_MODIFIER
            * df.CONTRACT_MODIFIER
            * df.CAUSE_MODIFIER
            * df.DIAGNOSIS_MODIFIER
            * df.MARGIN_SELECT,
        )
    )[col_order]
    return rate_tbl


def get_ctr_ultimate(idi_occupation_class, gender):
    """Generate ctr ultimate rates."""
    query = "IDI_OCCUPATION_CLASS==@idi_occupation_class and GENDER==@gender"
    margin = get_margin()["DURATION_2+"]
    tbl = (
        get_base_ultimate_ctr()
        .query(query)
        .assign(
            MARGIN_ULTIMATE=1 - margin,
            ULTIMATE_CTR=lambda df: df.BASE_ULTIMATE_CTR * df.MARGIN_ULTIMATE,
        )
    )
    return tbl[["AGE_ATTAINED", "BASE_ULTIMATE_CTR", "MARGIN_ULTIMATE", "ULTIMATE_CTR"]]
