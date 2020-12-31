from footings import (
    def_meta,
    def_parameter,
    model,
)
from footings_idi_model.attributes import (
    param_assumption_set,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
    modifier_ctr,
    modifier_interest,
)
from footings_idi_model.schemas import disabled_base_schema


@model
class DLRBasePM:
    """The DLR base parameters, sensitivities, and meta."""

    # parameters
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    policy_id = def_parameter(**disabled_base_schema["policy_id"])
    claim_id = def_parameter(**disabled_base_schema["claim_id"])
    gender = def_parameter(**disabled_base_schema["gender"])
    birth_dt = def_parameter(**disabled_base_schema["birth_dt"])
    incurred_dt = def_parameter(**disabled_base_schema["incurred_dt"])
    termination_dt = def_parameter(**disabled_base_schema["termination_dt"])
    elimination_period = def_parameter(**disabled_base_schema["elimination_period"])
    idi_contract = def_parameter(**disabled_base_schema["idi_contract"])
    idi_benefit_period = def_parameter(**disabled_base_schema["idi_benefit_period"])
    idi_diagnosis_grp = def_parameter(**disabled_base_schema["idi_diagnosis_grp"])
    idi_occupation_class = def_parameter(**disabled_base_schema["idi_occupation_class"])
    cola_percent = def_parameter(**disabled_base_schema["cola_percent"])
    benefit_amount = def_parameter(**disabled_base_schema["benefit_amount"])

    # sensitivities
    ctr_modifier = modifier_ctr
    interest_modifier = modifier_interest

    # meta
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time
    model_mode = def_meta(
        meta="DLR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )
