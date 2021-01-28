import os
from functools import lru_cache
import json

import pandas as pd

from footings.utils import once

directory, filename = os.path.split(__file__)


@once
def read_base_incidence():
    file = os.path.join(directory, "2013-idi-base-incidence.csv")
    dtypes = {
        "TYPE": "category",
        "IDI_OCCUPATION_CLASS": "category",
        "GENDER": "category",
    }
    return pd.read_csv(file, dtype=dtypes)


@lru_cache(256)
def get_base_incidence(idi_contract, idi_occupation_class, gender, elimination_period):
    tbl = read_base_incidence()
    incidence_cols = [
        "IDI_OCCUPATION_CLASS",
        "GENDER",
        "ELIMINATION_PERIOD",
        "AGE_ATTAINED",
    ]
    if idi_contract == "AO":
        tbl = tbl[tbl.TYPE == "Acc"]
    elif idi_contract == "SO":
        tbl = tbl[tbl.TYPE == "Sck"]
    else:
        tbl = tbl.groupby(incidence_cols, as_index=False).sum()
    return tbl[
        (tbl.IDI_OCCUPATION_CLASS == idi_occupation_class)
        & (tbl.GENDER == gender)
        & (tbl.ELIMINATION_PERIOD == elimination_period)
    ][incidence_cols + ["INCIDENCES"]]


@once
def read_benefit_period_modifiers():
    file = os.path.join(directory, "2013-idi-benefit-period-modifier.csv")
    dtypes = {
        "IDI_OCCUPATION_CLASS": "category",
        "IDI_BENEFIT_PERIOD": "category",
    }
    return pd.read_csv(file, dtype=dtypes)


@lru_cache(maxsize=512)
def get_benefit_period_modifier(
    idi_occupation_class, idi_benefit_period, elimination_period
):
    tbl = read_benefit_period_modifiers()
    return tbl[
        (tbl.IDI_OCCUPATION_CLASS == idi_occupation_class)
        & (tbl.IDI_BENEFIT_PERIOD == idi_benefit_period)
        & (tbl.ELIMINATION_PERIOD == elimination_period)
    ]["BENEFIT_PERIOD_MODIFIER"].iat[0]


@once
def read_contract_modifiers():
    file = os.path.join(directory, "2013-idi-contract-modifier.csv")
    dtypes = {"IDI_CONTRACT": "category"}
    return pd.read_csv(file, dtype=dtypes)


@lru_cache(maxsize=4)
def get_contract_modifier(idi_contract):
    tbl = read_contract_modifiers()
    return tbl[tbl.IDI_CONTRACT == idi_contract]["CONTRACT_MODIFIER"].iat[0]


@once
def read_market_modifiers():
    file = os.path.join(directory, "2013-idi-market-modifier.csv")
    dtypes = {"IDI_MARKET": "category"}
    return pd.read_csv(file, dtype=dtypes)


@lru_cache(maxsize=4)
def get_market_modifier(idi_market):
    tbl = read_market_modifiers()
    return tbl[tbl.IDI_MARKET == idi_market]["MARKET_MODIFIER"].iat[0]


@once
def read_tobacco_modifiers():
    file = os.path.join(directory, "2013-idi-tobacco-modifier.csv")
    dtypes = {
        "IDI_OCCUPATION_CLASS": "category",
        "GENDER": "category",
        "TOBACCO_USAGE": "category",
    }
    return pd.read_csv(file, dtype=dtypes)


@lru_cache(maxsize=256)
def get_tobacco_modifier(idi_occupation_class, gender, tobacco_usage):
    tbl = read_tobacco_modifiers()
    return tbl[
        (tbl.IDI_OCCUPATION_CLASS == idi_occupation_class)
        & (tbl.GENDER == gender)
        & (tbl.TOBACCO_USAGE == tobacco_usage)
    ]["TOBACCO_MODIFIER"].iat[0]


@once
def get_margin_adjustment():
    file = os.path.join(directory, "margin.json")
    with open(file, "r") as f:
        margin_temp = json.load(f)
    return 1 + margin_temp["DURATION_1+"]


def _stat_gaap_incidence(
    idi_contract,
    idi_occupation_class,
    idi_market,
    idi_benefit_period,
    tobacco_usage,
    elimination_period,
    gender,
):

    prod_cols = [
        "INCIDENCES",
        "BENEFIT_PERIOD_MODIFIER",
        "CONTRACT_MODIFIER",
        "MARKET_MODIFIER",
        "TOBACCO_MODIFIER",
        "MARGIN_ADJUSTMENT",
    ]

    frame = get_base_incidence(
        idi_contract, idi_occupation_class, gender, elimination_period
    ).reset_index()
    frame["IDI_CONTRACT"] = idi_contract
    frame["IDI_BENEFIT_PERIOD"] = idi_benefit_period
    frame["IDI_MARKET"] = idi_market
    frame["TOBACCO_USAGE"] = tobacco_usage
    frame["BENEFIT_PERIOD_MODIFIER"] = get_benefit_period_modifier(
        idi_occupation_class, idi_benefit_period, elimination_period
    )
    frame["CONTRACT_MODIFIER"] = get_contract_modifier(idi_contract)
    frame["MARKET_MODIFIER"] = get_market_modifier(idi_market)
    frame["TOBACCO_MODIFIER"] = get_tobacco_modifier(
        idi_occupation_class, gender, tobacco_usage
    )
    frame["MARGIN_ADJUSTMENT"] = get_margin_adjustment()
    frame["INCIDENCE_RATE"] = frame[prod_cols].prod(axis=1).div(1000)

    return frame[
        [
            "IDI_BENEFIT_PERIOD",
            "IDI_CONTRACT",
            "IDI_MARKET",
            "IDI_OCCUPATION_CLASS",
            "TOBACCO_USAGE",
            "ELIMINATION_PERIOD",
            "GENDER",
            "AGE_ATTAINED",
            "INCIDENCES",
            "BENEFIT_PERIOD_MODIFIER",
            "CONTRACT_MODIFIER",
            "MARKET_MODIFIER",
            "TOBACCO_MODIFIER",
            "MARGIN_ADJUSTMENT",
            "INCIDENCE_RATE",
        ]
    ]
