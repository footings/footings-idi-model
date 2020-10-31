import numpy as np
import pandas as pd

from footings import (
    define_asset,
    define_meta,
    define_modifier,
    define_parameter,
    define_placeholder,
    Footing,
    step,
    model,
)
from footings.tools import create_frame, calculate_age
from ..attributes import (
    param_assumption_set,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
)
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..assumptions.get_claim_term_rates import get_ctr_table
from ..schemas import disabled_base_schema

#########################################################################################
# Create frame
#########################################################################################


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


def _filter_frame(frame, valuation_dt):
    return frame[frame["DATE_ED"] >= valuation_dt]


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
    "_calculate_age_incurred",
    "_calculate_start_pay_date",
    "_create_frame",
    "_calculate_vd_weights",
    "_get_ctr_table",
    "_calculate_lives",
    "_calculate_cola_adjustment",
    "_calculate_monthly_benefits",
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
    ctr_modifier = define_modifier(
        default=1.0, dtype=float, description="Modifier for CTR."
    )
    interest_modifier = define_modifier(
        default=1.0, dtype=float, description="Interest rate modifier."
    )
    age_incurred = define_placeholder(
        dtype=int, description="The age when the claim was incurred for the claimant."
    )
    start_pay_date = define_placeholder(
        dtype=pd.Timestamp, description="The date payments start for claimants."
    )
    ctr_table = define_placeholder(dtype=pd.DataFrame, description=" ")
    frame = define_asset(dtype=pd.DataFrame, description="The reserve schedule.")
    mode = define_meta(meta="DLR", dtype=str, description="The model mode which is DLR.")
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    @step(uses=["birth_dt", "incurred_dt"], impacts=["age_incurred"])
    def _calculate_age_incurred(self):
        """Calcuate the age when claimant becomes disabled."""
        self.age_incurred = calculate_age(self.birth_dt, self.incurred_dt, method="ACB")

    @step(uses=["incurred_dt", "elimination_period"], impacts=["start_pay_date"])
    def _calculate_start_pay_date(self):
        self.start_pay_date = self.incurred_dt + pd.DateOffset(
            days=self.elimination_period
        )

    @step(
        uses=["birth_dt", "incurred_dt", "termination_dt", "valuation_dt"],
        impacts=["frame"],
    )
    def _create_frame(self):
        """Create frame projected out to termination date to model reserves."""
        fixed = {
            "frequency": "M",
            "col_date_nm": "DATE_BD",
            "duration_year": "DURATION_YEAR",
            "duration_month": "DURATION_MONTH",
        }

        self.frame = (
            create_frame(start_dt=self.incurred_dt, end_dt=self.termination_dt, **fixed)
            .pipe(_assign_end_date)
            .pipe(_filter_frame, self.valuation_dt)
            .assign(
                AGE_ATTAINED=lambda df: calculate_age(
                    self.birth_dt, df["DATE_BD"], method="ACB"
                ),
            )[["DATE_BD", "DATE_ED", "AGE_ATTAINED", "DURATION_YEAR", "DURATION_MONTH",]]
        )

    @step(uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_vd_weights(self):
        dur_n_days = (self.frame["DATE_ED"].iat[0] - self.frame["DATE_BD"].iat[0]).days
        self.frame["WT_BD"] = (
            self.frame["DATE_ED"].iat[0] - self.valuation_dt
        ).days / dur_n_days
        self.frame["WT_ED"] = 1 - self.frame["WT_BD"]

    @step(
        uses=[
            "assumption_set",
            "mode",
            "idi_benefit_period",
            "idi_contract",
            "idi_diagnosis_grp",
            "idi_occupation_class",
            "gender",
            "elimination_period",
            "age_incurred",
            "cola_percent",
        ],
        impacts=["ctr_table"],
    )
    def _get_ctr_table(self):
        """Get claim termination rate (CTR) table."""
        self.ctr_table = get_ctr_table(
            assumption_set=self.assumption_set, mode=self.mode, model_object=self,
        ).assign(
            CTR_MODIFIER=self.ctr_modifier, FINAL_CTR=lambda df: df.CTR * df.CTR_MODIFIER
        )

    @step(uses=["frame", "ctr_table"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate the begining, middle, and ending lives for each duration."""
        self.frame = self.frame.merge(
            self.ctr_table[["DURATION_MONTH", "FINAL_CTR"]],
            how="left",
            on=["DURATION_MONTH"],
        )
        self.frame["LIVES_ED"] = (1 - self.frame["CTR"]).cumprod()
        self.frame["LIVES_BD"] = self.frame["LIVES_ED"].shift(1, fill_value=1)
        self.frame["LIVES_MD"] = self.frame[["LIVES_BD", "LIVES_ED"]].mean(axis=1)
        bd_cols, ed_cols = ["WT_BD", "LIVES_BD"], ["WT_ED", "LIVES_ED"]
        self.frame["LIVES_VD_ADJ"] = 1 / (
            self.frame[bd_cols].prod(axis=1) + self.frame[ed_cols].prod(axis=1)
        )

    @step(uses=["frame", "cola_percent"], impacts=["frame"])
    def _calculate_cola_adjustment(self):
        """Calculate cost of living adjustment adjustment (COLA)."""
        max_duration = self.frame[self.frame["AGE_ATTAINED"] == 65]["DURATION_YEAR"]
        if max_duration.size > 0:
            upper = max_duration.iat[0]
            power = self.frame["DURATION_YEAR"].clip(upper=upper)
        else:
            power = self.frame["DURATION_YEAR"]
        self.frame["COLA_ADJUSTMENT"] = (1 + self.cola_percent) ** (power - 1)

    @step(uses=["frame", "benefit_amount"], impacts=["frame"])
    def _calculate_monthly_benefits(self):
        """Calculate the monthly benefit amount for each duration."""
        days_period = (self.frame.DATE_ED - self.frame.DATE_BD).dt.days
        condlist = [
            self.start_pay_date > self.frame.DATE_ED,
            (self.start_pay_date < self.valuation_dt)
            & (self.valuation_dt < self.frame.DATE_ED)
            & (self.valuation_dt >= self.frame.DATE_BD),
            (self.start_pay_date > self.valuation_dt)
            & (self.start_pay_date < self.frame.DATE_ED)
            & (self.start_pay_date >= self.frame.DATE_BD),
            (self.termination_dt > self.frame.DATE_BD)
            & (self.termination_dt <= self.frame.DATE_ED),
        ]
        choicelist = [
            0,
            (self.frame.DATE_ED - self.valuation_dt).dt.days / days_period,
            (self.frame.DATE_ED - self.start_pay_date).dt.days / days_period,
            (self.termination_dt - self.frame.DATE_BD).dt.days / days_period,
        ]
        self.frame["BENEFIT_FACTOR"] = np.select(condlist, choicelist, default=1.0)
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame[["BENEFIT_FACTOR", "COLA_ADJUSTMENT"]]
            .prod(axis=1)
            .mul(self.benefit_amount)
            .round(2)
        )

    @step(uses=["frame", "incurred_dt"], impacts=["frame"])
    def _calculate_discount(self):
        """Calculate begining, middle, and ending discount factor for each duration."""
        interest_rate = get_interest_rate(self.incurred_dt) * self.interest_modifier
        min_duration = self.frame["DURATION_MONTH"].min()
        self.frame["DAYS_TO_ED"] = (self.frame["DURATION_MONTH"] - min_duration + 1) * 30
        self.frame["DAYS_TO_MD"] = self.frame["DAYS_TO_ED"] - 15
        self.frame["DISCOUNT_MD"] = 1 / (1 + interest_rate) ** (
            self.frame["DAYS_TO_MD"] / 360
        )
        self.frame["DISCOUNT_ED"] = 1 / (1 + interest_rate) ** (
            self.frame["DAYS_TO_ED"] / 360
        )
        self.frame["DISCOUNT_BD"] = self.frame["DISCOUNT_ED"].shift(1, fill_value=1)
        bd_cols, ed_cols = ["WT_BD", "DISCOUNT_BD"], ["WT_ED", "DISCOUNT_ED"]
        self.frame["DISCOUNT_VD_ADJ"] = 1 / (
            self.frame[bd_cols].prod(axis=1) + self.frame[ed_cols].prod(axis=1)
        )

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        """Calculate present value of future benefits (PVFB)."""
        prod_columns = ["BENEFIT_AMOUNT", "LIVES_MD", "DISCOUNT_MD"]
        self.frame["PVFB_BD"] = (
            self.frame[prod_columns].prod(axis=1).iloc[::-1].cumsum().round(2)
        )
        self.frame["PVFB_ED"] = self.frame["PVFB_BD"].shift(-1, fill_value=0)
        bd_cols, ed_cols = ["WT_BD", "PVFB_BD"], ["WT_ED", "PVFB_ED"]
        self.frame["PVFB_VD"] = self.frame[bd_cols].prod(axis=1) + self.frame[
            ed_cols
        ].prod(axis=1)

    @step(uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_dlr(self):
        """Calculate disabled life reserves (DLR)."""
        prod_cols = ["PVFB_VD", "DISCOUNT_VD_ADJ", "LIVES_VD_ADJ"]
        self.frame["DLR"] = self.frame[prod_cols].prod(axis=1).round(2)
        self.frame["DATE_DLR"] = [
            self.valuation_dt + pd.DateOffset(months=period)
            for period in range(0, self.frame.shape[0])
        ]

    @step(
        uses=["frame", "policy_id", "run_date_time", "model_version", "last_commit"],
        impacts=["frame"],
    )
    def _to_output(self):
        """Reduce output to only needed columns."""
        self.frame = self.frame.assign(
            POLICY_ID=self.policy_id,
            RUN_DATE_TIME=self.run_date_time,
            MODEL_VERSION=self.model_version,
            LAST_COMMIT=self.last_commit,
        )[OUTPUT_COLS]
