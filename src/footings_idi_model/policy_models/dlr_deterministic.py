import pandas as pd

from footings import define_parameter, use, build_model

from ..functions.dlr import (
    create_dlr_frame,
    calculate_ctr,
    calculate_cola_adjustment,
    calculate_monthly_benefits,
    calculate_lives,
    calculate_discount,
    calculate_pvfb,
    calculate_dlr,
    to_output_format,
)
from ..schemas import disabled_life_schema, disabled_life_columns

__all__ = [
    "create_dlr_frame",
    "calculate_ctr",
    "calculate_cola_adjustment",
    "calculate_monthly_benefits",
    "calculate_lives",
    "calculate_discount",
    "calculate_pvfb",
    "calculate_dlr",
    "to_output_format",
]

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
        "args": {
            "frame": use("calculate-ctr"),
            "cola_percent": param_cola_percent,
            "incurred_dt": param_incurred_dt,
        },
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
        "name": "calculate-lives",
        "function": calculate_lives,
        "args": {"frame": use("calculate-monthly-benefit")},
    },
    {
        "name": "calculate-discount",
        "function": calculate_discount,
        "args": {"frame": use("calculate-lives"), "incurred_dt": param_incurred_dt,},
    },
    {
        "name": "calculate-pvfb",
        "function": calculate_pvfb,
        "args": {"frame": use("calculate-discount")},
    },
    {
        "name": "calculate-dlr",
        "function": calculate_dlr,
        "args": {"frame": use("calculate-pvfb"), "valuation_dt": param_valuation_dt},
    },
    {
        "name": "to-output-format",
        "function": to_output_format,
        "args": {"frame": use("calculate-dlr")},
    },
]

#########################################################################################
# model
#########################################################################################

NAME = "DLRDeterminsticPolicyModel"
DESCRIPTION = """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual
disability insurance (IDI) valuation standard.

The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

The key assumption underlying the model is -

* `Termination Rates` - the probability of an individual going off claim.

"""
dlr_deterministic_model = build_model(name=NAME, description=DESCRIPTION, steps=steps)
