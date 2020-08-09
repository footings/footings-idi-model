import pandas as pd

from footings import define_parameter, use, build_model

from ..functions.active_lives import (
    create_alr_frame,
    calculate_lives,
    calculate_discount,
    calculate_incidence_rate,
    model_disabled_lives,
    calculate_claim_cost,
    calculate_rop_payment_intervals,
    calculate_rop_future_claims,
    calculate_rop_future_total_claims,
    calculate_rop_benefits,
    calculate_pvfb,
    calculate_pvnfb,
    calculate_alr_from_issue,
    calculate_alr_from_valuation_date,
    to_output_format,
)

from ..schemas import (
    active_lives_base_schema,
    active_lives_base_columns,
    active_lives_rider_schema,
    active_lives_rider_columns,
)

__all__ = [
    "create_alr_frame",
    "calculate_lives",
    "calculate_discount",
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
param_net_benefit_method = define_parameter(
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
base_attributes = {}
for col, val in zip(active_lives_base_columns, active_lives_base_schema["columns"]):
    record = {
        col.lower(): {
            "name": val["name"].lower(),
            "description": val["description"],
            "dtype": val["dtype"],
        }
    }
    base_attributes.update(record)

rider_attributes = {}
for col, val in zip(active_lives_rider_columns, active_lives_rider_schema["columns"]):
    record = {
        col.lower(): {
            "name": val["name"].lower(),
            "description": val["description"],
            "dtype": val["dtype"],
        }
    }
    rider_attributes.update(record)

# base params
param_policy_id = define_parameter(**base_attributes["policy_id"])
param_gender = define_parameter(**base_attributes["gender"])
param_birth_dt = define_parameter(**base_attributes["birth_dt"])
param_tobacco_usage = define_parameter(**base_attributes["tobacco_usage"])
param_policy_start_dt = define_parameter(**base_attributes["policy_start_dt"])
param_policy_end_dt = define_parameter(**base_attributes["policy_end_dt"])
param_elimination_period = define_parameter(**base_attributes["elimination_period"])
param_idi_market = define_parameter(**base_attributes["idi_market"])
param_idi_contract = define_parameter(**base_attributes["idi_contract"])
param_idi_benefit_period = define_parameter(**base_attributes["idi_benefit_period"])
param_idi_occupation_class = define_parameter(**base_attributes["idi_occupation_class"])
param_cola_percent = define_parameter(**base_attributes["cola_percent"])
param_benefit_end_id = define_parameter(**base_attributes["benefit_end_id"])
param_gross_premium = define_parameter(**base_attributes["gross_premium"])
param_benefit_amount = define_parameter(**base_attributes["benefit_amount"])

# rider params
param_rop_return_frequency = define_parameter(**rider_attributes["rop_return_frequency"])
param_rop_return_percentage = define_parameter(
    **rider_attributes["rop_return_percentage"]
)
param_rop_claims_paid = define_parameter(**rider_attributes["rop_claims_paid"])
param_rop_future_claims_start_dt = define_parameter(
    **rider_attributes["rop_future_claims_start_dt"]
)


#########################################################################################
# individual steps
#########################################################################################

CREATE_FRAME = {
    "name": "create-frame",
    "function": create_alr_frame,
    "args": {
        "valuation_dt": param_valuation_dt,
        "policy_id": param_policy_id,
        "gender": param_gender,
        "birth_dt": param_birth_dt,
        "tobacco_usage": param_tobacco_usage,
        "policy_start_dt": param_policy_start_dt,
        "policy_end_dt": param_policy_end_dt,
        "elimination_period": param_elimination_period,
        "idi_market": param_idi_market,
        "idi_contract": param_idi_contract,
        "idi_benefit_period": param_idi_benefit_period,
        "idi_occupation_class": param_idi_occupation_class,
        "benefit_end_id": param_benefit_end_id,
        "gross_premium": param_gross_premium,
        "benefit_amount": param_benefit_amount,
    },
}

CALCULATE_LIVES = {
    "name": "calculate-lives",
    "function": calculate_lives,
    "args": {"frame": use("create-frame"), "assumption_set": param_assumption_set,},
}

CALCULATE_DISCOUNT = {
    "name": "calculate-discount",
    "function": calculate_discount,
    "args": {"frame": use("calculate-lives"), "policy_start_dt": param_policy_start_dt,},
}

CALCULATE_INCIDENCE_RATE = {
    "name": "calculate-incidence-rate",
    "function": calculate_incidence_rate,
    "args": {"frame": use("calculate-discount"), "idi_contract": param_idi_contract},
}

MODEL_DISABLED_LIVES = {
    "name": "modeled-disabled-lives",
    "function": model_disabled_lives,
    "args": {
        "frame": use("calculate-incidence-rate"),
        "assumption_set": param_assumption_set,
        "birth_dt": param_birth_dt,
        "elimination_period": param_elimination_period,
        "idi_benefit_period": param_idi_benefit_period,
        "cola_percent": param_cola_percent,
    },
}

CALCULATE_BENEFIT_COST_ALR = {
    "name": "calculate-benefit-cost",
    "function": calculate_claim_cost,
    "args": {
        "frame": use("calculate-incidence-rate"),
        "modeled_disabled_lives": use("modeled-disabled-lives"),
    },
}

CALCULATE_ROP_PAYMENT_INTERVALS = {
    "name": "calculate-rop-payment-intervals",
    "function": calculate_rop_payment_intervals,
    "args": {
        "frame": use("calculate-incidence-rate"),
        "rop_return_frequency": param_rop_return_frequency,
    },
}

CALCULATE_ROP_FUTURE_CLAIMS = {
    "name": "calculate-rop-future-claims",
    "function": calculate_rop_future_claims,
    "args": {
        "frame": use("calculate-rop-payment-intervals"),
        "modeled_disabled_lives": use("modeled-disabled-lives"),
        "rop_return_frequency": param_rop_return_frequency,
        "rop_future_benefit_start_dt": param_rop_future_claims_start_dt,
    },
}

CALCULATE_ROP_FUTURE_TOTAL_CLAIMS = {
    "name": "calculate-rop-future-total-claims",
    "function": calculate_rop_future_total_claims,
    "args": {
        "frame": use("calculate-rop-payment-intervals"),
        "rop_future_claim_payments": use("calculate-rop-future-claims"),
    },
}

CALCULATE_BENEFIT_COST_ROP = {
    "name": "calculate-benefit-cost",
    "function": calculate_rop_benefits,
    "args": {
        "frame": use("calculate-rop-payment-intervals"),
        "rop_claims_paid": param_rop_claims_paid,
        "rop_return_percentage": param_rop_return_percentage,
        "rop_future_total_claims": use("calculate-rop-future-total-claims"),
        "rop_future_benefit_start_dt": param_rop_future_claims_start_dt,
    },
}

CALCULATE_PVFB = {
    "name": "calculate-pvfb",
    "function": calculate_pvfb,
    "args": {"frame": use("calculate-benefit-cost")},
}

CALCULATE_PVFNB = {
    "name": "calculate-pvnfb",
    "function": calculate_pvnfb,
    "args": {
        "frame": use("calculate-pvfb"),
        "net_benefit_method": param_net_benefit_method,
        # "premium_pay_to_age": "",
    },
}

CALCULATE_RESERVE_FROM_ISSUE = {
    "name": "calculate-reserve-from-issue",
    "function": calculate_alr_from_issue,
    "args": {"frame": use("calculate-pvnfb")},
}

CALCULATE_RESERVE_FROM_VALUATION_DATE = {
    "name": "calculate-reserve-from-valuation-date",
    "function": calculate_alr_from_valuation_date,
    "args": {
        "frame": use("calculate-reserve-from-issue"),
        "valuation_dt": param_valuation_dt,
    },
}

TO_OUTPUT_FORMAT = {
    "name": "to-output-format",
    "function": to_output_format,
    "args": {"frame": use("calculate-reserve-from-valuation-date")},
}

#########################################################################################
# alr model
#########################################################################################

ALR_NAME = "ALRDeterministicPolicyModel"
ALR_DESCRIPTION = """ A policy model to calculate active life reserves (ALRs) using the 2013 individual
disability insurance (IDI) valuation standard.

The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

The key assumptions underlying the model are -

* `Incidence Rates` - The probablility of an individual becoming disabled.
* `Termination Rates` - Given an an individual is disabled, the probability of an individual going off claim.

"""
ALR_STEPS = [
    CREATE_FRAME,
    CALCULATE_LIVES,
    CALCULATE_DISCOUNT,
    CALCULATE_INCIDENCE_RATE,
    MODEL_DISABLED_LIVES,
    CALCULATE_BENEFIT_COST_ALR,
    CALCULATE_PVFB,
    CALCULATE_PVFNB,
    CALCULATE_RESERVE_FROM_ISSUE,
    CALCULATE_RESERVE_FROM_VALUATION_DATE,
    TO_OUTPUT_FORMAT,
]
alr_deterministic_model = build_model(
    name=ALR_NAME, description=ALR_DESCRIPTION, steps=ALR_STEPS
)

#########################################################################################
# rop model
#########################################################################################

ROP_NAME = "ROPDeterministicPolicyModel"
ROP_DESCRIPTION = """A policy model to calculate active life reserves (ALRs) using the 2013 individual
disability insurance (IDI) valuation standard.

The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

The key assumptions underlying the model are -

* `Incidence Rates` - The probablility of an individual becoming disabled.
* `Termination Rates` - Given an an individual is disabled, the probability of an individual going off claim.

"""
ROP_STEPS = [
    CREATE_FRAME,
    CALCULATE_LIVES,
    CALCULATE_DISCOUNT,
    CALCULATE_INCIDENCE_RATE,
    MODEL_DISABLED_LIVES,
    CALCULATE_ROP_PAYMENT_INTERVALS,
    CALCULATE_ROP_FUTURE_CLAIMS,
    CALCULATE_ROP_FUTURE_TOTAL_CLAIMS,
    CALCULATE_BENEFIT_COST_ROP,
    CALCULATE_PVFB,
    CALCULATE_PVFNB,
    CALCULATE_RESERVE_FROM_ISSUE,
    CALCULATE_RESERVE_FROM_VALUATION_DATE,
    TO_OUTPUT_FORMAT,
]
rop_deterministic_model = build_model(
    name=ROP_NAME, description=ROP_DESCRIPTION, steps=ROP_STEPS
)
