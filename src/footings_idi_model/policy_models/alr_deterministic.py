import pandas as pd

from footings import create_parameter, use, create_model

from ..functions.alr import (
    create_alr_frame,
    calculate_lives,
    calculate_discount,
    calculate_cola_adjustment,
    calculate_benefit_amount,
    calculate_incidence_rate,
    calculate_claim_cost,
    calculate_pvfb,
    calculate_pvnfb,
    calculate_alr_from_issue,
    calculate_alr_from_valuation_date,
    to_output_format,
)

from ..schemas import active_life_schema, active_life_columns

__all__ = [
    "create_alr_frame",
    "calculate_lives",
    "calculate_discount",
    "calculate_cola_adjustment",
    "calculate_benefit_amount",
    "calculate_incidence_rate",
    "calculate_claim_cost",
    "calculate_pvfb",
    "calculate_pvnfb",
    "calculate_alr_from_issue",
    "calculate_alr_from_valuation_date",
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
arg_net_benefit_method = create_parameter(
    name="net_benefit_method",
    description="""The net benefit method. Options are :

        * `NLP` = Net level premium
        * `PT1` = 1 year preliminary term
        * `PT2` = 2 year preliminary term
    """,
    dtype=str,
    allowed=["NLP", "PT1", "PT2"],
)

# create arguments from active life schema
al_attributes = {}
for col, val in zip(active_life_columns, active_life_schema["columns"]):
    record = {
        col.lower(): {
            "name": val["name"].lower(),
            "description": val["description"],
            "dtype": val["dtype"],
        }
    }
    al_attributes.update(record)

arg_policy_id = create_parameter(**al_attributes["policy_id"])
arg_gender = create_parameter(**al_attributes["gender"])
arg_birth_dt = create_parameter(**al_attributes["birth_dt"])
arg_tobacco_usage = create_parameter(**al_attributes["tobacco_usage"])
arg_issue_dt = create_parameter(**al_attributes["issue_dt"])
arg_termination_dt = create_parameter(**al_attributes["termination_dt"])
arg_elimination_period = create_parameter(**al_attributes["elimination_period"])
arg_idi_market = create_parameter(**al_attributes["idi_market"])
arg_idi_contract = create_parameter(**al_attributes["idi_contract"])
arg_idi_benefit_period = create_parameter(**al_attributes["idi_benefit_period"])
arg_idi_occupation_class = create_parameter(**al_attributes["idi_occupation_class"])
arg_cola_percent = create_parameter(**al_attributes["cola_percent"])
arg_benefit_amount = create_parameter(**al_attributes["benefit_amount"])


#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "create-alr-frame",
        "function": create_alr_frame,
        "args": {
            "valuation_dt": arg_valuation_dt,
            "policy_id": arg_policy_id,
            "gender": arg_gender,
            "birth_dt": arg_birth_dt,
            "tobacco_usage": arg_tobacco_usage,
            "issue_dt": arg_issue_dt,
            "termination_dt": arg_termination_dt,
            "elimination_period": arg_elimination_period,
            "idi_market": arg_idi_market,
            "idi_contract": arg_idi_contract,
            "idi_benefit_period": arg_idi_benefit_period,
            "idi_occupation_class": arg_idi_occupation_class,
        },
    },
    {
        "name": "calculate-lives",
        "function": calculate_lives,
        "args": {"frame": use("create-alr-frame"), "assumption_set": arg_assumption_set,},
    },
    {
        "name": "calculate-discount",
        "function": calculate_discount,
        "args": {"frame": use("calculate-lives"), "issue_dt": arg_issue_dt,},
    },
    {
        "name": "calculate-cola-adjustment",
        "function": calculate_cola_adjustment,
        "args": {"frame": use("calculate-discount"), "cola_percent": arg_cola_percent},
    },
    {
        "name": "calculate-benefit-amount",
        "function": calculate_benefit_amount,
        "args": {
            "frame": use("calculate-cola-adjustment"),
            "benefit_amount": arg_benefit_amount,
        },
    },
    {
        "name": "calculate-incidence-rate",
        "function": calculate_incidence_rate,
        "args": {"frame": use("calculate-benefit-amount"), "cause": "combined"},
    },
    {
        "name": "calculate-claim-cost",
        "function": calculate_claim_cost,
        "args": {
            "frame": use("calculate-incidence-rate"),
            "assumption_set": arg_assumption_set,
            "birth_dt": arg_birth_dt,
            "idi_benefit_period": arg_idi_benefit_period,
        },
    },
    {
        "name": "calculate-pvfb",
        "function": calculate_pvfb,
        "args": {"frame": use("calculate-claim-cost")},
    },
    {
        "name": "calculate-pvnfb",
        "function": calculate_pvnfb,
        "args": {
            "frame": use("calculate-pvfb"),
            "net_benefit_method": arg_net_benefit_method,
            # "premium_pay_to_age": "",
        },
    },
    {
        "name": "calculate-alr-from-issue",
        "function": calculate_alr_from_issue,
        "args": {"frame": use("calculate-pvnfb")},
    },
    {
        "name": "calculate-alr-from-valuation-date",
        "function": calculate_alr_from_valuation_date,
        "args": {
            "frame": use("calculate-alr-from-issue"),
            "valuation_dt": arg_valuation_dt,
        },
    },
    {
        "name": "to-output-format",
        "function": to_output_format,
        "args": {"frame": use("calculate-alr-from-valuation-date")},
    },
]

#########################################################################################
# model
#########################################################################################

NAME = "ALRDeterministicPolicyModel"
DESCRIPTION = "Calculate 2013 Valuation Standard ALR for a policy."
alr_deterministic_model = create_model(name=NAME, description=DESCRIPTION, steps=steps)
