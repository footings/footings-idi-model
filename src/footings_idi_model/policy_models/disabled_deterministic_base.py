import pandas as pd
from footings.actuarial_tools import calc_continuance, calc_discount, calc_pv
from footings.model import def_intermediate, def_meta, def_return, model, step
from footings.model_tools import (
    calculate_age,
    create_frame,
    frame_add_exposure,
    frame_add_weights,
)

from ..assumptions.get_claim_term_rates import get_ctr_table
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..data import (  # DisabledLivesRiderExtract,; DisabledLivesProjOutput,
    DisabledLivesBaseExtract,
    DisabledLivesValOutput,
)
from ..shared import (
    meta_last_commit,
    meta_model_version,
    meta_run_date_time,
    modifier_ctr,
    modifier_interest,
    param_assumption_set,
    param_valuation_dt,
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
    "_calculate_start_pay_dt",
    "_create_frame",
    "_calculate_age_attained",
    "_get_ctr_rates",
    "_calculate_benefit_cost",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_durational_dlr",
    "_calculate_valuation_dt_dlr",
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
    start_pay_dt = def_intermediate(
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
        impacts=["start_pay_dt"],
    )
    def _calculate_start_pay_dt(self):
        """Calculate date benefits start which is incurred date + elimination period days."""
        self.start_pay_dt = self.incurred_dt + pd.DateOffset(days=self.elimination_period)

    @step(
        name="Create Projected Frame",
        uses=["birth_dt", "incurred_dt", "termination_dt", "valuation_dt"],
        impacts=["frame"],
    )
    def _create_frame(self):
        """Create projected benefit frame from valuation date to termination date by duration month."""
        kwargs_frame = {
            "frequency": "M",
            "col_date_nm": "DATE_BD",
            "duration_year": "DURATION_YEAR",
            "duration_month": "DURATION_MONTH",
        }
        kwargs_wt = {
            "as_of_dt": self.valuation_dt,
            "begin_duration_col": "DATE_BD",
            "end_duration_col": "DATE_ED",
            "wt_current_name": "WT_BD",
            "wt_next_name": "WT_ED",
        }
        cols = [
            "DATE_BD",
            "DATE_ED",
            "DURATION_YEAR",
            "DURATION_MONTH",
            "WT_BD",
            "WT_ED",
        ]
        self.frame = (
            create_frame(self.incurred_dt, self.termination_dt, **kwargs_frame)
            .pipe(_assign_end_date)
            .pipe(_filter_frame, self.valuation_dt)
            .pipe(frame_add_weights, **kwargs_wt)
        )[cols]

    @step(name="Calculate Age Attained", uses=["frame", "birth_dt"], impacts=["frame"])
    def _calculate_age_attained(self):
        """Calculate age attained by policy duration on the frame."""
        self.frame["AGE_ATTAINED"] = calculate_age(
            self.birth_dt, self.frame["DATE_BD"], method="ALB"
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
    def _get_ctr_rates(self):
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
        # merge CTR
        self.frame = self.frame.merge(
            self.ctr_table[["DURATION_MONTH", "FINAL_CTR"]],
            how="left",
            on=["DURATION_MONTH"],
        )
        # calculate lives
        lives_ed = calc_continuance(self.frame["FINAL_CTR"])
        lives_bd = lives_ed.shift(1, fill_value=1)
        lives_md = (lives_bd + lives_ed) / 2

        # assign lives to frame
        self.frame["LIVES_BD"] = lives_bd
        self.frame["LIVES_MD"] = lives_md
        self.frame["LIVES_ED"] = lives_ed

    @step(
        name="Calculate Monthly Benefits",
        uses=[
            "frame",
            "valuation_dt",
            "start_pay_dt",
            "termination_dt",
            "benefit_amount",
        ],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate the benefit cost for each duration."""
        self.frame = frame_add_exposure(
            self.frame,
            begin_date=max(self.valuation_dt, self.start_pay_dt),
            end_date=self.termination_dt,
            exposure_name="EXPOSURE",
            begin_duration_col="DATE_BD",
            end_duration_col="DATE_ED",
        )
        self.frame["BENEFIT_AMOUNT"] = self.frame["EXPOSURE"] * self.benefit_amount

    @step(
        name="Calculate Discount Factors",
        uses=["frame", "incurred_dt"],
        impacts=["frame"],
    )
    def _calculate_discount(self):
        """Calculate beginning, middle, and ending discount factors for each duration."""
        base_int_rate = get_interest_rate(self.incurred_dt)
        self.frame["INTEREST_RATE_BASE"] = base_int_rate
        self.frame["INTEREST_RATE_MODIFIER"] = self.interest_modifier
        self.frame["INTEREST_RATE"] = (
            self.frame["INTEREST_RATE_BASE"] * self.frame["INTEREST_RATE_MODIFIER"]
        )
        self.frame["DISCOUNT_BD"] = calc_discount(
            self.frame["INTEREST_RATE"] / 12, t_adj=0
        )
        self.frame["DISCOUNT_MD"] = calc_discount(
            self.frame["INTEREST_RATE"] / 12, t_adj=0.5
        )
        self.frame["DISCOUNT_ED"] = calc_discount(self.frame["INTEREST_RATE"] / 12)

    @step(name="Calculate DLR", uses=["frame"], impacts=["frame"])
    def _calculate_durational_dlr(self):
        """Calculate durational life reserves (ALR) for each duration."""
        benefit_cols = ["BENEFIT_AMOUNT", "LIVES_MD", "DISCOUNT_MD"]
        self.frame["PVFB_BD"] = calc_pv(self.frame[benefit_cols].prod(axis=1))
        self.frame["PVFB_ED"] = self.frame["PVFB_BD"].shift(-1, fill_value=0)

    @step(name="Calculate DLR", uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_valuation_dt_dlr(self):
        """Calculate active life reserves (ALR) for each duration as of valuation date."""

        def dlr_date(period):
            return self.valuation_dt + pd.DateOffset(months=period)

        self.frame["DATE_DLR"] = pd.to_datetime(
            [dlr_date(period) for period in range(0, self.frame.shape[0])]
        )

        # calculate lives adj
        lives_bd = self.frame[["LIVES_BD", "WT_BD"]].prod(axis=1)
        lives_ed = self.frame[["LIVES_ED", "WT_ED"]].prod(axis=1)
        lives_adj = 1 / (lives_bd + lives_ed)
        self.frame["LIVES_ADJ"] = lives_adj

        # calculate discount adj
        discount_bd = self.frame[["DISCOUNT_BD", "WT_BD"]].prod(axis=1)
        discount_ed = self.frame[["DISCOUNT_ED", "WT_ED"]].prod(axis=1)
        discount_adj = 1 / (discount_bd + discount_ed)
        self.frame["DISCOUNT_ADJ"] = discount_adj

        # calculate DLR
        dlr_bd = self.frame[["PVFB_BD", "WT_BD"]].prod(axis=1)
        dlr_ed = self.frame[["PVFB_ED", "WT_ED"]].prod(axis=1)
        self.frame["DLR"] = ((dlr_bd + dlr_ed) / discount_adj / lives_adj).round(2)

    @step(
        name="Create Output Frame",
        uses=[
            "frame",
            "policy_id",
            "claim_id",
            "run_date_time",
            "model_version",
            "last_commit",
            "coverage_id",
        ],
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
