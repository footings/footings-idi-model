import pandas as pd

from footings.model import (
    def_meta,
    def_return,
    def_intermediate,
    step,
    model,
)
from footings.model_tools import (
    create_frame,
    calculate_age,
    frame_add_exposure,
    frame_add_weights,
)
from ..shared import (
    param_assumption_set,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
    modifier_ctr,
    modifier_interest,
)
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..assumptions.get_claim_term_rates import get_ctr_table
from ..data import (
    DisabledLivesBaseExtract,
    # DisabledLivesRiderExtract,
    DisabledLivesValOutput,
    # DisabledLivesProjOutput,
)


#########################################################################################
# Policy model parent (shared by both projection and valuation models)
#########################################################################################


@model
class DLRBasePMD:
    """DLR base parameters, sensitivities, and meta."""

    # parameters
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    policy_id = DisabledLivesBaseExtract.def_parameter("POLICY_ID")
    claim_id = DisabledLivesBaseExtract.def_parameter("CLAIM_ID")
    gender = DisabledLivesBaseExtract.def_parameter("GENDER")
    birth_dt = DisabledLivesBaseExtract.def_parameter("BIRTH_DT")
    incurred_dt = DisabledLivesBaseExtract.def_parameter("INCURRED_DT")
    termination_dt = DisabledLivesBaseExtract.def_parameter("TERMINATION_DT")
    elimination_period = DisabledLivesBaseExtract.def_parameter("ELIMINATION_PERIOD")
    idi_contract = DisabledLivesBaseExtract.def_parameter("IDI_CONTRACT")
    idi_benefit_period = DisabledLivesBaseExtract.def_parameter("IDI_BENEFIT_PERIOD")
    idi_diagnosis_grp = DisabledLivesBaseExtract.def_parameter("IDI_DIAGNOSIS_GRP")
    idi_occupation_class = DisabledLivesBaseExtract.def_parameter("IDI_OCCUPATION_CLASS")
    cola_percent = DisabledLivesBaseExtract.def_parameter("COLA_PERCENT")
    benefit_amount = DisabledLivesBaseExtract.def_parameter("BENEFIT_AMOUNT")

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


#########################################################################################
# Valuation Policy Model - Base
#########################################################################################

STEPS = [
    "_calculate_age_incurred",
    "_calculate_start_pay_date",
    "_create_frame",
    "_calculate_vd_weights",
    "_get_ctr_table",
    "_calculate_lives",
    "_calculate_monthly_benefits",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_dlr",
    "_to_output",
]


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


def _filter_frame(frame, valuation_dt):
    return frame[frame["DATE_ED"] >= valuation_dt]


@model(steps=STEPS)
class DValBasePMD(DLRBasePMD):
    """The disabled life reserve (DLR) valuation model for the base policy."""

    coverage_id = def_meta(
        meta="BASE",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    # intermediate objects
    age_incurred = def_intermediate(
        dtype=int, description="The age when the claim was incurred for the claimant."
    )
    start_pay_date = def_intermediate(
        dtype=pd.Timestamp, description="The date payments start for claimants."
    )
    ctr_table = def_intermediate(
        dtype=pd.DataFrame, description="The claim termination rate (CTR) table."
    )

    # return object
    frame = def_return(dtype=pd.DataFrame, description="The frame of projected reserves.")

    # steps
    @step(
        name="Calculate Age Incurred",
        uses=["birth_dt", "incurred_dt"],
        impacts=["age_incurred"],
    )
    def _calculate_age_incurred(self):
        """Calculate the age when claimant becomes disabled."""
        self.age_incurred = calculate_age(self.birth_dt, self.incurred_dt, method="ACB")

    @step(
        name="Calculate Benefit Start Date",
        uses=["incurred_dt", "elimination_period"],
        impacts=["start_pay_date"],
    )
    def _calculate_start_pay_date(self):
        """Calculate date benefits start which is incurred date + elimination period days."""
        self.start_pay_date = self.incurred_dt + pd.DateOffset(
            days=self.elimination_period
        )

    @step(
        name="Create Projected Frame",
        uses=["birth_dt", "incurred_dt", "termination_dt", "valuation_dt"],
        impacts=["frame"],
    )
    def _create_frame(self):
        """Create projected benefit frame from valuation date to termination date by duration month."""
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

    @step(
        name="Calculate Weights", uses=["frame", "valuation_dt"], impacts=["frame"],
    )
    def _calculate_vd_weights(self):
        """Calculate weights to assign to beginning and ending duration."""
        self.frame = frame_add_weights(
            self.frame,
            as_of_dt=self.valuation_dt,
            begin_duration_col="DATE_BD",
            end_duration_col="DATE_ED",
            wt_current_name="WT_BD",
            wt_next_name="WT_ED",
        )

    @step(
        name="Get CTR Table",
        uses=[
            "assumption_set",
            "model_mode",
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
        """Get claim termination rate (CTR) table based on assumption set."""
        self.ctr_table = get_ctr_table(
            assumption_set=self.assumption_set,
            model_mode=self.model_mode,
            model_object=self,
        ).assign(
            CTR_MODIFIER=self.ctr_modifier, FINAL_CTR=lambda df: df.CTR * df.CTR_MODIFIER
        )

    @step(name="Calculate Lives", uses=["frame", "ctr_table"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate the beginning, middle, and ending lives for each duration."""
        self.frame = self.frame.merge(
            self.ctr_table[["DURATION_MONTH", "FINAL_CTR"]],
            how="left",
            on=["DURATION_MONTH"],
        )
        self.frame["LIVES_ED"] = (1 - self.frame["FINAL_CTR"]).cumprod()
        self.frame["LIVES_BD"] = self.frame["LIVES_ED"].shift(1, fill_value=1)
        self.frame["LIVES_MD"] = self.frame[["LIVES_BD", "LIVES_ED"]].mean(axis=1)
        bd_cols, ed_cols = ["WT_BD", "LIVES_BD"], ["WT_ED", "LIVES_ED"]
        self.frame["LIVES_VD_ADJ"] = 1 / (
            self.frame[bd_cols].prod(axis=1) + self.frame[ed_cols].prod(axis=1)
        )

    @step(
        name="Calculate Monthly Benefits",
        uses=["frame", "benefit_amount"],
        impacts=["frame"],
    )
    def _calculate_monthly_benefits(self):
        """Calculate the monthly benefit amount for each duration."""
        self.frame = frame_add_exposure(
            self.frame,
            begin_date=max(self.valuation_dt, self.start_pay_date),
            end_date=self.termination_dt,
            exposure_name="BENEFIT_FACTOR",
            begin_duration_col="DATE_BD",
            end_duration_col="DATE_ED",
        )
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame["BENEFIT_FACTOR"].mul(self.benefit_amount).round(2)
        )

    @step(
        name="Calculate Discount Factors",
        uses=["frame", "incurred_dt"],
        impacts=["frame"],
    )
    def _calculate_discount(self):
        """Calculate beginning, middle, and ending discount factors for each duration."""
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

    @step(name="Calculate PVFB", uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        """Calculate present value of future benefits (PVFB)."""
        prod_columns = ["BENEFIT_AMOUNT", "LIVES_MD", "DISCOUNT_MD"]
        self.frame["PVFB_BD"] = (
            self.frame[prod_columns]
            .prod(axis=1)
            .iloc[::-1]
            .cumsum()
            .round(2)
            .clip(lower=0)
        )
        self.frame["PVFB_ED"] = self.frame["PVFB_BD"].shift(-1, fill_value=0)
        bd, ed = ["WT_BD", "PVFB_BD"], ["WT_ED", "PVFB_ED"]
        self.frame["PVFB_VD"] = self.frame[bd].prod(axis=1) + self.frame[ed].prod(axis=1)

    @step(name="Calculate DLR", uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_dlr(self):
        """Calculate disabled life reserves (DLR)."""
        prod_cols = ["PVFB_VD", "DISCOUNT_VD_ADJ", "LIVES_VD_ADJ"]
        self.frame["DLR"] = self.frame[prod_cols].prod(axis=1).round(2)
        self.frame["DATE_DLR"] = [
            self.valuation_dt + pd.DateOffset(months=period)
            for period in range(0, self.frame.shape[0])
        ]

    @step(
        name="Create Output Frame",
        uses=["frame", "policy_id", "run_date_time", "model_version", "last_commit"],
        impacts=["frame"],
    )
    def _to_output(self):
        """Reduce output to only needed columns."""
        self.frame = self.frame.assign(
            POLICY_ID=self.policy_id,
            CLAIM_ID=self.claim_id,
            SOURCE=self.__class__.__qualname__,
            RUN_DATE_TIME=self.run_date_time,
            MODEL_VERSION=self.model_version,
            LAST_COMMIT=self.last_commit,
            COVERAGE_ID=self.coverage_id,
            # set column order
        )[list(DisabledLivesValOutput.columns)]


#########################################################################################
# Projection Policy Model - Base
#########################################################################################


@model
class DProjBasePMD(DLRBasePMD):
    pass
