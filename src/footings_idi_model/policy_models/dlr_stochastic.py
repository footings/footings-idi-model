import pandas as pd
import numpy as np

from footings import define_parameter, use, build_model
from footings.tools import post_drop_columns

from ..functions.disabled_lives import (
    create_dlr_frame,
    calculate_ctr,
    calculate_cola_adjustment,
    calculate_monthly_benefits,
    calculate_discount,
    _sumprod_present_value,
)
from ..schemas import disabled_life_schema, disabled_life_columns


#########################################################################################
# arguments
#########################################################################################


param_valuation_dt = define_parameter(
    name="valuation_dt",
    description="The valuation date which reserves are based.",
    dtype=pd.Timestamp,
)
param_assumption_set = define_parameter(
    name="assumption_set",
    description="""The assumption set to use for running the model. Options are :
    
        * `stat`
        * `gaap`
        * `best-estimate`
    """,
    dtype=str,
    allowed=["stat", "gaap", "best-estimate"],
)

# create arguments from disabled life schema
dl_attributes = {}
for col, val in zip(disabled_life_columns, disabled_life_schema["columns"]):
    record = {
        col.lower(): {
            "name": val["name"].lower(),
            "description": val["description"],
            "dtype": val["dtype"],
        }
    }
    dl_attributes.update(record)

param_policy_id = define_parameter(**dl_attributes["policy_id"])
param_claim_id = define_parameter(**dl_attributes["claim_id"])
param_gender = define_parameter(**dl_attributes["gender"])
param_birth_dt = define_parameter(**dl_attributes["birth_dt"])
param_incurred_dt = define_parameter(**dl_attributes["incurred_dt"])
param_termination_dt = define_parameter(**dl_attributes["termination_dt"])
param_elimination_period = define_parameter(**dl_attributes["elimination_period"])
param_idi_contract = define_parameter(**dl_attributes["idi_contract"])
param_idi_benefit_period = define_parameter(**dl_attributes["idi_benefit_period"])
param_idi_diagnosis_grp = define_parameter(**dl_attributes["idi_diagnosis_grp"])
param_idi_occupation_class = define_parameter(**dl_attributes["idi_occupation_class"])
param_cola_percent = define_parameter(**dl_attributes["cola_percent"])
param_benefit_amount = define_parameter(**dl_attributes["benefit_amount"])

param_n_simulations = define_parameter(name="n_simulations", default=1000, dtype=int)
param_seed = define_parameter(name="seed", default=42, dtype=int)

#########################################################################################
# functions
#########################################################################################


def simulate_inforce(frame: pd.DataFrame, n_simulations: int, seed: int):

    np.random.seed(seed=seed)
    cols = list(frame.columns)

    def simulate(df, run):
        rows = df.shape[0]
        df = df.copy()
        df["RUN"] = run
        df["RANDOM"] = np.random.uniform(size=rows)
        df["TEMP_INFORCE"] = np.select([df["CTR"] > df["RANDOM"]], [0], default=1.0)
        df["TEMP_CUM"] = df["TEMP_INFORCE"].cumsum()
        df.loc[(df["TEMP_CUM"] != df.index.values + 1), "TEMP_INFORCE"] = 0.0
        condlist = [(df["TEMP_INFORCE"].shift(1) == 1) & (df["TEMP_INFORCE"] == 0)]
        df["INFORCE"] = np.select(condlist, [0.5], default=df["TEMP_INFORCE"])
        return df[["RUN"] + cols + ["RANDOM", "TEMP_INFORCE", "INFORCE"]]

    frame = pd.concat([simulate(frame, n) for n in range(1, n_simulations + 1)])
    return frame


def calculate_val_date_items(frame: pd.DataFrame, valuation_dt: pd.Timestamp):
    """Calculate benefits paid using simulated inforce.
    
    Returns
    -------
    pd.DataFrame
        The DataFrame with an added column BENEFITS_PAID.
    """
    cols_bd, cols_ed = ["WT_BD", "DISCOUNT_BD"], ["WT_ED", "DISCOUNT_ED"]
    frame["DISCOUNT_VD_ADJ"] = 1 / (
        frame[cols_bd].prod(axis=1) + frame[cols_ed].prod(axis=1)
    )
    frame["DATE_DLR"] = [
        valuation_dt + pd.DateOffset(months=period) for period in range(0, frame.shape[0])
    ]
    return frame


def simulate_benefits(frame: pd.DataFrame, n_simulations: int, seed: int):

    np.random.seed(seed=seed)
    cols = list(frame.columns)
    cols_add = [
        "RANDOM",
        "TEMP_INFORCE",
        "INFORCE",
        "BENEFITS_PAID",
        "PVFB_VD",
        "DLR",
    ]

    def simulate(df, run):
        rows = df.shape[0]
        df = df.copy()
        df["RUN"] = run
        df["RANDOM"] = np.random.uniform(size=rows)
        df["TEMP_INFORCE"] = np.select([df["CTR"] > df["RANDOM"]], [0], default=1.0)
        df["TEMP_CUM"] = df["TEMP_INFORCE"].cumsum()
        df.loc[(df["TEMP_CUM"] != df.index.values + 1), "TEMP_INFORCE"] = 0.0
        condlist = [(df["TEMP_INFORCE"].shift(1) == 1) & (df["TEMP_INFORCE"] == 0)]
        df["INFORCE"] = np.select(condlist, [0.5], default=df["TEMP_INFORCE"])
        df["BENEFITS_PAID"] = df["BENEFIT_AMOUNT"] * df["INFORCE"]
        prod_columns = ["BENEFITS_PAID", "DISCOUNT_MD"]
        df["PVFB_BD"] = _sumprod_present_value(df, prod_columns).round(2)
        df["PVFB_ED"] = df["PVFB_BD"].shift(-1, fill_value=0)
        cols_bd, cols_ed = ["WT_BD", "PVFB_BD"], ["WT_ED", "PVFB_ED"]
        df["PVFB_VD"] = df[cols_bd].prod(axis=1) + df[cols_ed].prod(axis=1)
        df["DLR"] = df[["PVFB_VD", "DISCOUNT_VD_ADJ"]].prod(axis=1).round(2)

        df = df[df.INFORCE > 0]
        return df[["RUN"] + cols + cols_add]

    frame = pd.concat([simulate(frame, n) for n in range(1, n_simulations + 1)])
    return frame


OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "POLICY_ID",
    "RUN",
    "DATE_BD",
    "DATE_ED",
    "DURATION_YEAR",
    "DURATION_MONTH",
    "BENEFIT_AMOUNT",
    "CTR",
    "DISCOUNT_BD",
    "DISCOUNT_MD",
    "DISCOUNT_ED",
    "BENEFITS_PAID",
    "PVFB_VD",
    "DISCOUNT_VD_ADJ",
    "DATE_DLR",
    "DLR",
]


def to_output_format(frame: pd.DataFrame):
    """Create model output.

    Returns
    -------
    pd.DataFrame
        A DataFrame with present value of benefits paid at time 0 for each simulated run.
    pd.DataFrame
        A DataFrame with a distribution of expected benefits paid by duration.
    dict
        A dictonary of any policies that error running the model.
    """
    return frame[OUTPUT_COLS]


#########################################################################################
# steps
#########################################################################################


steps = [
    {
        "name": "create-dlr-frame",
        "function": create_dlr_frame,
        "args": {
            "valuation_dt": param_valuation_dt,
            "policy_id": param_policy_id,
            "claim_id": param_claim_id,
            "gender": param_gender,
            "birth_dt": param_birth_dt,
            "incurred_dt": param_incurred_dt,
            "termination_dt": param_termination_dt,
            "elimination_period": param_elimination_period,
            "idi_contract": param_idi_contract,
            "idi_benefit_period": param_idi_benefit_period,
            "idi_diagnosis_grp": param_idi_diagnosis_grp,
            "idi_occupation_class": param_idi_occupation_class,
            "cola_percent": param_cola_percent,
        },
    },
    {
        "name": "calculate-ctr",
        "function": calculate_ctr,
        "args": {
            "frame": use("create-dlr-frame"),
            "assumption_set": param_assumption_set,
            "mode": "DLR",
        },
    },
    {
        "name": "calculate-cola-adjustment",
        "function": calculate_cola_adjustment,
        "args": {"frame": use("calculate-ctr"), "cola_percent": param_cola_percent},
    },
    {
        "name": "calculate-monthly-benefit",
        "function": calculate_monthly_benefits,
        "args": {
            "frame": use("calculate-cola-adjustment"),
            "benefit_amount": param_benefit_amount,
        },
    },
    {
        "name": "calculate-discount",
        "function": calculate_discount,
        "args": {
            "frame": use("calculate-monthly-benefit"),
            "incurred_dt": param_incurred_dt,
        },
    },
    {
        "name": "calculate-val-date-items",
        "function": calculate_val_date_items,
        "args": {"frame": use("calculate-discount"), "valuation_dt": param_valuation_dt,},
    },
    {
        "name": "simulate-benefits",
        "function": simulate_benefits,
        "args": {
            "frame": use("calculate-val-date-items"),
            "n_simulations": param_n_simulations,
            "seed": param_seed,
        },
    },
    {
        "name": "to-output-format",
        "function": to_output_format,
        "args": {"frame": use("simulate-benefits")},
    },
]

#########################################################################################
# model
#########################################################################################

NAME = "DLRStochasticPolicyModel"
DESCRIPTION = """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual
disability insurance (IDI) valuation standard.

The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

The key assumption underlying the model is -

* `Termination Rates` - the probability of an individual going off claim.

"""
dlr_stochastic_model = build_model(name=NAME, description=DESCRIPTION, steps=steps)
