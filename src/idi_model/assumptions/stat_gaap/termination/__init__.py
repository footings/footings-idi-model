"""Prepare termination assumptions"""

import os
import json
from functools import lru_cache

import pandas as pd

directory, filename = os.path.split(__file__)

# contract modifier
contract_file = os.path.join(directory, "2013-idi-contract-modifier.csv")


@lru_cache(maxsize=2)
def get_contract_modifier(file):
    """Get contract modifier"""
    return pd.read_csv(file)


# benefit period modifier
benefit_period_file = os.path.join(directory, "2013-idi-benefit-period-modifier.csv")


@lru_cache(maxsize=2)
def get_benefit_period_modifier(file):
    """Get benefit period modifier"""
    return pd.read_csv(file)


# cause modifier
diagnosis_file = os.path.join(directory, "2013-idi-diagnosis-modifier.csv")


@lru_cache(maxsize=2)
def get_diagnosis_modifier(file):
    """Get diagnosis modifier"""
    return pd.read_csv(file)


# cause modifier
cause_file = os.path.join(directory, "2013-idi-cause-modifier.csv")


@lru_cache(maxsize=2)
def get_cause_modifier(file):
    """Get cause modifier"""
    return pd.read_csv(file)


# select ctr
select_file = os.path.join(directory, "2013-idi-base-ctr-select.csv")


@lru_cache(maxsize=2)
def get_select_ctr(file):
    """Get select CTR"""
    dtypes = {"IDI_OCCUPATION_CLASS": object}
    return pd.read_csv(file, dtype=dtypes)


# ultimate ctr
ultimate_file = os.path.join(directory, "2013-idi-base-ctr-ultimate.csv")


@lru_cache(maxsize=2)
def get_ultimate_ctr(file):
    """Get ultimate CTR"""
    return pd.read_csv(file)


# margin
margin_file = os.path.join(directory, "margin.json")


@lru_cache(maxsize=2)
def get_margin(file):
    """Get termination margin"""
    with open(file, "r") as f:
        margin_temp = json.load(f)
    margin = [1 - margin_temp["DURATION_1"]] + [
        1 - margin_temp["DURATION_2+"] for i in range(1, 100)
    ]
    tbl = pd.DataFrame({"DURATION_YEAR": range(1, 101), "MARGIN_ADJUSTMENT": margin})
    return tbl
