from footings import (
    def_parameter,
    model,
)

from ..attributes import (
    param_assumption_set,
    param_net_benefit_method,
    param_valuation_dt,
    param_withdraw_table,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
    modifier_interest,
    modifier_incidence,
    modifier_withdraw,
    modifier_ctr,
)
from ..schemas import active_base_schema


@model
class ALRBasePMD:
    """ALR base parameters, sensitivities, and meta."""

    # parameters
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method
    withdraw_table = param_withdraw_table
    policy_id = def_parameter(**active_base_schema["policy_id"])
    gender = def_parameter(**active_base_schema["gender"])
    birth_dt = def_parameter(**active_base_schema["birth_dt"])
    tobacco_usage = def_parameter(**active_base_schema["tobacco_usage"])
    policy_start_dt = def_parameter(**active_base_schema["policy_start_dt"])
    policy_end_dt = def_parameter(**active_base_schema["policy_end_dt"])
    elimination_period = def_parameter(**active_base_schema["elimination_period"])
    idi_market = def_parameter(**active_base_schema["idi_market"])
    idi_contract = def_parameter(**active_base_schema["idi_contract"])
    idi_benefit_period = def_parameter(**active_base_schema["idi_benefit_period"])
    idi_occupation_class = def_parameter(**active_base_schema["idi_occupation_class"])
    cola_percent = def_parameter(**active_base_schema["cola_percent"])
    gross_premium = def_parameter(**active_base_schema["gross_premium"])
    gross_premium_freq = def_parameter(**active_base_schema["gross_premium_freq"])
    benefit_amount = def_parameter(**active_base_schema["benefit_amount"])

    # sensitivities
    ctr_modifier = modifier_ctr
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence
    withdraw_modifier = modifier_withdraw

    # meta
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time
