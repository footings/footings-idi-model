"""Prepare incidence assumptions"""

import os
from functools import lru_cache
import json

import pandas as pd

directory, filename = os.path.split(__file__)

# benefit period modifier
benefit_period_file = os.path.join(directory, "2013-idi-benefit-period-modifier.csv")


@lru_cache(maxsize=2)
def get_benefit_period_modifier(file):
    """Get benefit period modifier"""
    return pd.read_csv(file)


# contract modifier
contract_file = os.path.join(directory, "2013-idi-contract-modifier.csv")


@lru_cache(maxsize=2)
def get_contract_modifier(file):
    """Get contract modifier"""
    return pd.read_csv(file)


# market modifier
market_file = os.path.join(directory, "2013-idi-market-modifier.csv")


@lru_cache(maxsize=2)
def get_market_modifier(file):
    """Get market modifier"""
    return pd.read_csv(file)


# tobacco modifier
tobacco_file = os.path.join(directory, "2013-idi-tobacco-modifier.csv")


@lru_cache(maxsize=2)
def get_tobacco_modifier(file):
    """Get tobacco modifier"""
    return pd.read_csv(file)


# base incidence
incidence_file = os.path.join(directory, "2013-idi-base-incidence.csv")


@lru_cache(maxsize=4)
def get_base_incidence(file, cause):
    """Get base incidence"""
    tbl = pd.read_csv(file)
    if cause == "combined":
        cols = ["IDI_OCCUPATION_CLASS", "GENDER", "ELIMINATION_PERIOD", "AGE_ATTAINED"]
        return tbl.groupby(cols).sum()
    if cause == "accident":
        return tbl[tbl.TYPE == "Acc"]
    if cause == "sickness":
        return tbl[tbl.TYPE == "Sck"]
    raise ValueError(f"The cause [{cause}] is not recognized. See documentation.")


# margin
margin_file = os.path.join(directory, "margin.json")


@lru_cache(maxsize=2)
def get_margin(file):
    """Get incidence margin"""
    with open(file, "r") as f:
        margin_temp = json.load(f)
    margin = 1 + margin_temp["DURATION_1+"]
    tbl = pd.DataFrame({"DURATION_YEAR": range(1, 101)}).assign(MARGIN_ADJUSTMENT=margin)
    return tbl
