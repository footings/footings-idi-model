import pandas as pd

from footings import create_parameter, use, create_model

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

arg_valuation_dt = create_parameter(
    name="valuation_dt",
    description="The valuation date which reserves are based.",
    dtype=pd.Timestamp,
)
arg_assumption_set = create_parameter(
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

arg_policy_id = create_parameter(**dl_attributes["policy_id"])
arg_claim_id = create_parameter(**dl_attributes["claim_id"])
arg_gender = create_parameter(**dl_attributes["gender"])
arg_birth_dt = create_parameter(**dl_attributes["birth_dt"])
arg_incurred_dt = create_parameter(**dl_attributes["incurred_dt"])
arg_termination_dt = create_parameter(**dl_attributes["termination_dt"])
arg_elimination_period = create_parameter(**dl_attributes["elimination_period"])
arg_idi_contract = create_parameter(**dl_attributes["idi_contract"])
arg_idi_benefit_period = create_parameter(**dl_attributes["idi_benefit_period"])
arg_idi_diagnosis_grp = create_parameter(**dl_attributes["idi_diagnosis_grp"])
arg_idi_occupation_class = create_parameter(**dl_attributes["idi_occupation_class"])
arg_cola_percent = create_parameter(**dl_attributes["cola_percent"])
arg_benefit_amount = create_parameter(**dl_attributes["benefit_amount"])

#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "create-dlr-frame",
        "function": create_dlr_frame,
        "args": {
            "valuation_dt": arg_valuation_dt,
            "policy_id": arg_policy_id,
            "claim_id": arg_claim_id,
            "gender": arg_gender,
            "birth_dt": arg_birth_dt,
            "incurred_dt": arg_incurred_dt,
            "termination_dt": arg_termination_dt,
            "elimination_period": arg_elimination_period,
            "idi_contract": arg_idi_contract,
            "idi_benefit_period": arg_idi_benefit_period,
            "idi_diagnosis_grp": arg_idi_diagnosis_grp,
            "idi_occupation_class": arg_idi_occupation_class,
            "cola_percent": arg_cola_percent,
        },
    },
    {
        "name": "calculate-ctr",
        "function": calculate_ctr,
        "args": {
            "frame": use("create-dlr-frame"),
            "assumption_set": arg_assumption_set,
            "mode": "DLR",
        },
    },
    {
        "name": "calculate-cola-adjustment",
        "function": calculate_cola_adjustment,
        "args": {
            "frame": use("calculate-ctr"),
            "cola_percent": arg_cola_percent,
            "incurred_dt": arg_incurred_dt,
        },
    },
    {
        "name": "calculate-monthly-benefit",
        "function": calculate_monthly_benefits,
        "args": {
            "frame": use("calculate-cola-adjustment"),
            "benefit_amount": arg_benefit_amount,
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
        "args": {"frame": use("calculate-lives"), "incurred_dt": arg_incurred_dt,},
    },
    {
        "name": "calculate-pvfb",
        "function": calculate_pvfb,
        "args": {"frame": use("calculate-discount")},
    },
    {
        "name": "calculate-dlr",
        "function": calculate_dlr,
        "args": {"frame": use("calculate-pvfb"), "valuation_dt": arg_valuation_dt},
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
DESCRIPTION = "Calculate 2013 Valuation Standard DLR for a policy."
dlr_deterministic_model = create_model(name=NAME, description=DESCRIPTION, steps=steps)
