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

from ..functions.disabled_lives import (
    create_dlr_frame,
    calculate_ctr,
    calculate_cola_adjustment,
    calculate_monthly_benefits,
    calculate_lives,
    calculate_discount,
    calculate_pvfb,
    calculate_dlr,
)
from ..attributes import (
    param_assumption_set,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
)
from ..schemas import disabled_base_schema


OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "POLICY_ID",
    "DATE_BD",
    "DATE_ED",
    "DURATION_YEAR",
    "DURATION_MONTH",
    "BENEFIT_AMOUNT",
    "CTR",
    "LIVES_BD",
    "LIVES_MD",
    "LIVES_ED",
    "DISCOUNT_BD",
    "DISCOUNT_MD",
    "DISCOUNT_ED",
    "PVFB_BD",
    "PVFB_ED",
    "DATE_DLR",
    "DLR",
]


STEPS = [
    "_create_frame",
    "_calculate_ctr",
    "_calculate_cola_adjustment",
    "_calculate_monthly_benefits",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_dlr",
    "_to_output",
]


@model(steps=STEPS)
class DLRDeterministicPolicyModel(Footing):
    """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual disability insurance (IDI) valuation standard. \n
    
    The model is configured to use different assumptions sets - stat, gaap, or best-estimate. \n

    The key assumption underlying the model is -

    * `Termination Rates` - the probability of an individual going off claim.

    """

    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    policy_id = define_parameter(**disabled_base_schema["policy_id"])
    claim_id = define_parameter(**disabled_base_schema["claim_id"])
    gender = define_parameter(**disabled_base_schema["gender"])
    birth_dt = define_parameter(**disabled_base_schema["birth_dt"])
    incurred_dt = define_parameter(**disabled_base_schema["incurred_dt"])
    termination_dt = define_parameter(**disabled_base_schema["termination_dt"])
    elimination_period = define_parameter(**disabled_base_schema["elimination_period"])
    idi_contract = define_parameter(**disabled_base_schema["idi_contract"])
    idi_benefit_period = define_parameter(**disabled_base_schema["idi_benefit_period"])
    idi_diagnosis_grp = define_parameter(**disabled_base_schema["idi_diagnosis_grp"])
    idi_occupation_class = define_parameter(
        **disabled_base_schema["idi_occupation_class"]
    )
    cola_percent = define_parameter(**disabled_base_schema["cola_percent"])
    benefit_amount = define_parameter(**disabled_base_schema["benefit_amount"])
    ctr_modifier = define_modifier(default=1.0, dtype=float, description="Modifier for CTR.")
    frame = define_asset(dtype=pd.DataFrame, description="The reserve schedule.")
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    @step(
        uses=[
            "valuation_dt",
            "policy_id",
            "claim_id",
            "gender",
            "birth_dt",
            "incurred_dt",
            "termination_dt",
            "elimination_period",
            "idi_contract",
            "idi_benefit_period",
            "idi_diagnosis_grp",
            "idi_occupation_class",
            "cola_percent",
        ],
        impacts=["frame"],
    )
    def _create_frame(self):
        """Create frame projected out to termination date to model reserves."""
        self.frame = create_dlr_frame(
            valuation_dt=self.valuation_dt,
            policy_id=self.policy_id,
            claim_id=self.claim_id,
            gender=self.gender,
            birth_dt=self.birth_dt,
            incurred_dt=self.incurred_dt,
            termination_dt=self.termination_dt,
            elimination_period=self.elimination_period,
            idi_contract=self.idi_contract,
            idi_benefit_period=self.idi_benefit_period,
            idi_diagnosis_grp=self.idi_diagnosis_grp,
            idi_occupation_class=self.idi_occupation_class,
            cola_percent=self.cola_percent,
        )

    @step(uses=["frame", "assumption_set"], impacts=["frame"])
    def _calculate_ctr(self):
        """Calculate claim termination reserve (CTR)."""
        self.frame = calculate_ctr(
            frame=self.frame, assumption_set=self.assumption_set, mode="DLR",
        )

    @step(uses=["frame", "cola_percent"], impacts=["frame"])
    def _calculate_cola_adjustment(self):
        """Calculate cost of living adjustment (COLA)."""
        self.frame = calculate_cola_adjustment(
            frame=self.frame, cola_percent=self.cola_percent
        )

    @step(uses=["frame", "benefit_amount"], impacts=["frame"])
    def _calculate_monthly_benefits(self):
        """Calculate projected monthly benefits."""
        self.frame = calculate_monthly_benefits(
            frame=self.frame, benefit_amount=self.benefit_amount
        )

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate projected lives inforce."""
        self.frame = calculate_lives(frame=self.frame)

    @step(uses=["frame", "incurred_dt"], impacts=["frame"])
    def _calculate_discount(self):
        """Calculate discount rate."""
        self.frame = calculate_discount(frame=self.frame, incurred_dt=self.incurred_dt)

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        """Calculate present value of future benefits (PVFB)."""
        self.frame = calculate_pvfb(frame=self.frame)

    @step(uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_dlr(self):
        """Calculate disabled life reserve."""
        self.frame = calculate_dlr(frame=self.frame, valuation_dt=self.valuation_dt)

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Reduce output to only needed columns."""
        return self.frame[OUTPUT_COLS]
