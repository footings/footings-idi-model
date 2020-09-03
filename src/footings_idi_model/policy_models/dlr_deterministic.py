import pandas as pd

from footings import (
    define_parameter,
    define_modifier,
    define_asset,
    Footing,
    model,
    link,
    use_doc,
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
from ..parameters import (
    param_assumption_set,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
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


@model(steps=STEPS, auto_doc=True)
class DLRDeterminsticPolicyModel(Footing):
    """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual
    disability insurance (IDI) valuation standard.

    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

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
    ctr_modifier = define_modifier()
    frame = define_asset()

    @use_doc(create_dlr_frame, link=True)
    def _create_frame(self):
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

    @use_doc(calculate_ctr, link=True)
    def _calculate_ctr(self):
        self.frame = calculate_ctr(
            frame=self.frame, assumption_set=self.assumption_set, mode="DLR",
        )

    @use_doc(calculate_cola_adjustment, link=True)
    def _calculate_cola_adjustment(self):
        self.frame = calculate_cola_adjustment(
            frame=self.frame, cola_percent=self.cola_percent
        )

    @use_doc(calculate_monthly_benefits, link=True)
    def _calculate_monthly_benefits(self):
        self.frame = calculate_monthly_benefits(
            frame=self.frame, benefit_amount=self.benefit_amount
        )

    @use_doc(calculate_lives, link=True)
    def _calculate_lives(self):
        self.frame = calculate_lives(frame=self.frame)

    @use_doc(calculate_discount, link=True)
    def _calculate_discount(self):
        self.frame = calculate_discount(frame=self.frame, incurred_dt=self.incurred_dt)

    @use_doc(calculate_pvfb, link=True)
    def _calculate_pvfb(self):
        self.frame = calculate_pvfb(frame=self.frame)

    @use_doc(calculate_dlr, link=True)
    def _calculate_dlr(self):
        self.frame = calculate_dlr(frame=self.fame, valuation_dt=self.valuation_dt)

    @link(["frame"])
    def _to_output(self):
        """Create model output.

        Returns
        -------
        pd.DataFrame
            The final frame.
        """
        return self.frame[OUTPUT_COLS]
