import pandas as pd

from footings import (
    define_asset,
    define_meta,
    define_modifier,
    define_parameter,
    Footing,
    step,
    model,
)

from ..functions.active_lives import (
    create_alr_frame,
    calculate_lives,
    calculate_discount,
    calculate_incidence_rate,
    model_disabled_lives,
    calculate_claim_cost,
    calculate_rop_payment_intervals,
    calculate_rop_future_disabled_claims,
    calculate_rop_expected_claim_payments,
    calculate_rop_benefits,
    calculate_pvfb,
    calculate_pvnfb,
    calculate_alr,
)
from ..attributes import (
    param_assumption_set,
    param_net_benefit_method,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
)
from ..schemas import active_base_schema, active_rider_schema


OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "POLICY_ID",
    "COVERAGE_ID",
    "DATE_BD",
    "DATE_ED",
    "DURATION_YEAR",
    "LIVES_BD",
    "LIVES_MD",
    "LIVES_ED",
    "DISCOUNT_BD",
    "DISCOUNT_MD",
    "DISCOUNT_ED",
    "BENEFIT_AMOUNT",
    "INCIDENCE_RATE",
    "BENEFIT_COST",
    "PVFB",
    "PVFNB",
    "ALR_BD",
    "ALR_ED",
    "DATE_ALR",
    "ALR",
]


BASE_STEPS = [
    "_create_frame",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_incidence_rate",
    "_model_disabled_lives",
    "_calculate_benefit_cost",
    "_calculate_pvfb",
    "_calculate_pvfnb",
    "_calculate_alr",
    "_to_output",
]


@model(steps=BASE_STEPS)
class ALRDeterministicPolicyModel(Footing):
    """ A policy model to calculate active life reserves (ALRs) using the 2013 individual
    disability insurance (IDI) valuation standard.

    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

    The key assumptions underlying the model are -

    * `Incidence Rates` - The probablility of an individual becoming disabled.
    * `Termination Rates` - Given an an individual is disabled, the probability of an individual going off claim.

    """

    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method
    policy_id = define_parameter(**active_base_schema["policy_id"])
    coverage_id = define_parameter(**active_base_schema["coverage_id"])
    gender = define_parameter(**active_base_schema["gender"])
    birth_dt = define_parameter(**active_base_schema["birth_dt"])
    tobacco_usage = define_parameter(**active_base_schema["tobacco_usage"])
    policy_start_dt = define_parameter(**active_base_schema["policy_start_dt"])
    policy_end_dt = define_parameter(**active_base_schema["policy_end_dt"])
    elimination_period = define_parameter(**active_base_schema["elimination_period"])
    idi_market = define_parameter(**active_base_schema["idi_market"])
    idi_contract = define_parameter(**active_base_schema["idi_contract"])
    idi_benefit_period = define_parameter(**active_base_schema["idi_benefit_period"])
    idi_occupation_class = define_parameter(**active_base_schema["idi_occupation_class"])
    benefit_end_id = define_parameter(**active_base_schema["benefit_end_id"])
    cola_percent = define_parameter(**active_base_schema["cola_percent"])
    gross_premium = define_parameter(**active_base_schema["gross_premium"])
    benefit_amount = define_parameter(**active_base_schema["benefit_amount"])
    lapse_modifier = define_modifier(default=1.0)
    interest_modifier = define_modifier(default=1.0)
    incidence_modifier = define_modifier(default=1.0)
    modeled_disabled_lives = define_asset(default=1.0)
    frame = define_asset(dtype=pd.DataFrame)
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    @step(
        uses=[
            "frame",
            "assumption_set",
            "valuation_dt",
            "policy_id",
            "coverage_id",
            "gender",
            "tobacco_usage",
            "birth_dt",
            "policy_start_dt",
            "policy_end_dt",
            "elimination_period",
            "idi_market",
            "idi_contract",
            "idi_benefit_period",
            "idi_occupation_class",
            "benefit_end_id",
            "gross_premium",
            "benefit_amount",
        ],
        impacts=["frame"],
    )
    def _create_frame(self):
        self.frame = create_alr_frame(
            valuation_dt=self.valuation_dt,
            policy_id=self.policy_id,
            coverage_id=self.coverage_id,
            gender=self.gender,
            tobacco_usage=self.tobacco_usage,
            birth_dt=self.birth_dt,
            policy_start_dt=self.policy_start_dt,
            policy_end_dt=self.policy_end_dt,
            elimination_period=self.elimination_period,
            idi_market=self.idi_market,
            idi_contract=self.idi_contract,
            idi_benefit_period=self.idi_benefit_period,
            idi_occupation_class=self.idi_occupation_class,
            benefit_end_id=self.benefit_end_id,
            gross_premium=self.gross_premium,
            benefit_amount=self.benefit_amount,
        )

    @step(uses=["frame", "assumption_set"], impacts=["frame"])
    def _calculate_lives(self):
        self.frame = calculate_lives(assumption_set=self.assumption_set, frame=self.frame)

    @step(uses=["frame", "policy_start_dt"], impacts=["frame"])
    def _calculate_discount(self):
        self.frame = calculate_discount(
            frame=self.frame, policy_start_dt=self.policy_start_dt
        )

    @step(uses=["frame", "idi_contract"], impacts=["frame"])
    def _calculate_incidence_rate(self):
        self.frame = calculate_incidence_rate(
            frame=self.frame, idi_contract=self.idi_contract
        )

    @step(
        uses=[
            "frame",
            "assumption_set",
            "birth_dt",
            "elimination_period",
            "idi_benefit_period",
            "cola_percent",
        ],
        impacts=["modeled_disabled_lives"],
    )
    def _model_disabled_lives(self):
        self.modeled_disabled_lives = model_disabled_lives(
            frame=self.frame,
            assumption_set=self.assumption_set,
            birth_dt=self.birth_dt,
            elimination_period=self.elimination_period,
            idi_benefit_period=self.idi_benefit_period,
            cola_percent=self.cola_percent,
        )

    @step(uses=["frame", "modeled_disabled_lives"], impacts=["frame"])
    def _calculate_benefit_cost(self):
        self.frame = calculate_claim_cost(
            frame=self.frame, modeled_disabled_lives=self.modeled_disabled_lives
        )

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        self.frame = calculate_pvfb(self.frame)

    @step(uses=["frame", "net_benefit_method"], impacts=["frame"])
    def _calculate_pvfnb(self):
        self.frame = calculate_pvnfb(
            frame=self.frame, net_benefit_method=self.net_benefit_method
        )

    @step(uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_alr(self):
        self.frame = calculate_alr(self.frame, valuation_dt=self.valuation_dt)

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Return the calculated frame with attributes covering the policy, duration, and ALR.

        Parameters
        ----------
        frame : pd.DataFrame

        Returns
        -------
        pd.DataFrame
            The final DataFrame. 
        """

        return self.frame[OUTPUT_COLS]

    def _return(self):
        return self.frame


ROP_STEPS = [
    "_create_frame",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_incidence_rate",
    "_model_disabled_lives",
    "_calculate_rop_payment_intervals",
    "_calculate_rop_future_disabled_claims",
    "_calculate_rop_expected_claim_payments",
    "_calculate_benefit_cost",
    "_calculate_pvfb",
    "_calculate_pvfnb",
    "_calculate_reserve_from_issue",
    "_calculate_reserve_from_valuation_date",
    "_to_output_format",
]


# @model(steps=ROP_STEPS)
class ROPDeterministicPolicyModel(ALRDeterministicPolicyModel):
    """[summary]
    """

    rop_return_frequency = define_parameter(**active_rider_schema["rop_return_frequency"])
    rop_return_percentage = define_parameter(
        **active_rider_schema["rop_return_percentage"]
    )
    rop_claims_paid = define_parameter(**active_rider_schema["rop_claims_paid"])
    rop_future_claims_start_dt = define_parameter(
        **active_rider_schema["rop_future_claims_start_dt"]
    )
    rop_future_claims_frame = define_asset()

    @step(uses=["frame", "rop_return_frequency"], impacts=["frame"])
    def _calculate_rop_payment_intervals(self):
        self.frame = calculate_rop_payment_intervals(
            frame=self.frame, rop_return_frequency=self.rop_return_frequency
        )

    @step(uses=["frame", "modeled_disabled_lives"], impacts=["rop_future_claims_frame"])
    def _calculate_rop_future_disabled_claims(self):
        self.rop_future_claims_frame = calculate_rop_future_disabled_claims(
            frame=self.frame,
            modeled_disabled_lives=self.modeled_disabled_lives,
            rop_future_claims_start_dt=self.rop_future_claims_start_dt,
        )

    @step(uses=["frame", "rop_future_claims_frame"], impacts=["frame"])
    def _calculate_rop_expected_claim_payments(self):
        self.frame = calculate_rop_expected_claim_payments(
            frame=self.frame, rop_future_claims_frame=self.rop_future_claims_frame
        )

    @step(
        uses=[
            "frame",
            "rop_claims_paid",
            "rop_return_percentage",
            "rop_expected_claim_payments",
            "rop_future_claims_start_dt",
        ],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        self.frame = calculate_rop_benefits(
            frame=self.frame,
            rop_claims_paid=self.rop_claims_paid,
            rop_return_percentage=self.rop_return_percentage,
            rop_expected_claim_payments=self.rop_future_claims_frame,
            rop_future_claims_start_dt=self.rop_future_claims_start_dt,
        )
