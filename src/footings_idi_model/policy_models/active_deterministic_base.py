from datetime import date
from inspect import getfullargspec

import pandas as pd
from footings.actuarial_tools import (
    calc_continuance,
    calc_discount,
    calc_interpolation,
    calc_pv,
    calc_pvfnb,
)
from footings.exceptions import ModelRunError
from footings.jigs import create_foreach_jig
from footings.model import def_intermediate, def_meta, def_return, model, step
from footings.model_tools import (
    calculate_age,
    convert_to_records,
    create_frame,
    frame_add_weights,
)

from ..assumptions.get_incidence_rates import get_incidence_rates
from ..assumptions.get_withdraw_rates import get_withdraw_rates
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..data import (  # ActiveLivesROPRiderExtract,; ActiveLivesProjOutput,
    ActiveLivesBaseExtract,
    ActiveLivesValOutput,
)
from ..shared import (
    meta_last_commit,
    meta_model_version,
    meta_run_date_time,
    modifier_ctr,
    modifier_incidence,
    modifier_interest,
    modifier_withdraw,
    param_assumption_set,
    param_net_benefit_method,
    param_valuation_dt,
    param_withdraw_table,
)
from .disabled_deterministic_base import STEPS as CC_STEPS
from .disabled_deterministic_base import DValBasePMD

#########################################################################################
# Policy model parent (shared by both projection and valuation models)
#########################################################################################


@model
class ALRBasePMD:
    """ALR base parameters, sensitivities, and meta."""

    # parameters
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method
    withdraw_table = param_withdraw_table
    policy_id = ActiveLivesBaseExtract.def_parameter("POLICY_ID")
    coverage_id = ActiveLivesBaseExtract.def_parameter("COVERAGE_ID")
    gender = ActiveLivesBaseExtract.def_parameter("GENDER")
    birth_dt = ActiveLivesBaseExtract.def_parameter("BIRTH_DT")
    tobacco_usage = ActiveLivesBaseExtract.def_parameter("TOBACCO_USAGE")
    policy_start_dt = ActiveLivesBaseExtract.def_parameter("POLICY_START_DT")
    policy_end_dt = ActiveLivesBaseExtract.def_parameter("POLICY_END_DT")
    elimination_period = ActiveLivesBaseExtract.def_parameter("ELIMINATION_PERIOD")
    idi_market = ActiveLivesBaseExtract.def_parameter("IDI_MARKET")
    idi_contract = ActiveLivesBaseExtract.def_parameter("IDI_CONTRACT")
    idi_benefit_period = ActiveLivesBaseExtract.def_parameter("IDI_BENEFIT_PERIOD")
    idi_occupation_class = ActiveLivesBaseExtract.def_parameter("IDI_OCCUPATION_CLASS")
    cola_percent = ActiveLivesBaseExtract.def_parameter("COLA_PERCENT")
    premium_pay_to_dt = ActiveLivesBaseExtract.def_parameter("PREMIUM_PAY_TO_DT")
    gross_premium = ActiveLivesBaseExtract.def_parameter("GROSS_PREMIUM")
    gross_premium_freq = ActiveLivesBaseExtract.def_parameter("GROSS_PREMIUM_FREQ")
    benefit_amount = ActiveLivesBaseExtract.def_parameter("BENEFIT_AMOUNT")

    # sensitivities
    ctr_modifier = modifier_ctr
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence
    withdraw_modifier = modifier_withdraw

    # meta
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time


#########################################################################################
# Prepare Claim Cost Model - Base
#########################################################################################


@model(steps=CC_STEPS)
class ActiveLifeBaseClaimCostModel(DValBasePMD):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


def _constant_params():
    kwargs = getfullargspec(ActiveLifeBaseClaimCostModel).kwonlyargs
    kwargs.remove("incurred_dt")
    kwargs.remove("valuation_dt")
    return tuple(kwargs)


claim_cost_model = create_foreach_jig(
    ActiveLifeBaseClaimCostModel,
    iterator_name="records",
    iterator_keys=("policy_id", "valuation_dt",),
    pass_iterator_keys=("policy_id", "valuation_dt",),
    constant_params=_constant_params(),
)


#########################################################################################
# Valuation Policy Model - Base
#########################################################################################

STEPS = [
    "_calculate_age_issued",
    "_create_frame",
    "_calculate_age_attained",
    "_calculate_termination_dt",
    "_model_claim_cost",
    "_get_incidence_rate",
    "_get_withdraw_rates",
    "_calculate_premiums",
    "_calculate_benefit_cost",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_durational_alr",
    "_calculate_valuation_dt_alr",
    "_to_output",
]


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


@model(steps=STEPS)
class AValBasePMD(ALRBasePMD):
    """The active life reserve (ALR) valuation model for the base policy."""

    # meta
    claim_cost_model = def_meta(
        meta=claim_cost_model, dtype=callable, description="The claim cost model used.",
    )
    coverage_id = def_meta(
        meta="BASE",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    # intermediate objects
    age_issued = def_intermediate(
        dtype=date, description="The calculate age policy was issued."
    )
    withdraw_rates = def_intermediate(
        dtype=pd.DataFrame, description="The placholder for withdraw rates."
    )
    incidence_rates = def_intermediate(
        dtype=pd.DataFrame, description="The placholder for incidence rates."
    )
    modeled_claim_cost = def_intermediate(
        dtype=dict, description="The placholder for modeled disabled lives."
    )

    # return object
    frame = def_return(dtype=pd.DataFrame, description="The frame of projected reserves.")

    # steps
    @step(
        name="Calculate Issue Age",
        uses=["birth_dt", "policy_start_dt"],
        impacts=["age_issued"],
    )
    def _calculate_age_issued(self):
        """Calculate the age policy issued."""
        self.age_issued = calculate_age(self.birth_dt, self.policy_start_dt, method="ALB")

    @step(
        name="Create Projectetd Frame",
        uses=["policy_start_dt", "policy_end_dt"],
        impacts=["frame"],
    )
    def _create_frame(self):
        """Create projected benefit frame from policy start date to policy end date by duration year."""
        kwargs_frame = {
            "frequency": "Y",
            "col_date_nm": "DATE_BD",
            "duration_year": "DURATION_YEAR",
        }
        kwargs_wt = {
            "as_of_dt": self.valuation_dt,
            "begin_duration_col": "DATE_BD",
            "end_duration_col": "DATE_ED",
            "wt_current_name": "WT_BD",
            "wt_next_name": "WT_ED",
        }
        self.frame = (
            create_frame(self.policy_start_dt, self.policy_end_dt, **kwargs_frame)
            .pipe(_assign_end_date)
            .pipe(frame_add_weights, **kwargs_wt)
            .query("DATE_BD <= @self.policy_end_dt")
        )[["DATE_BD", "DATE_ED", "DURATION_YEAR", "WT_BD", "WT_ED"]]

    @step(name="Calculate Age Attained", uses=["frame", "birth_dt"], impacts=["frame"])
    def _calculate_age_attained(self):
        """Calculate age attained by policy duration on the frame."""
        self.frame["AGE_ATTAINED"] = calculate_age(
            self.birth_dt, self.frame["DATE_BD"], method="ALB"
        )

    @step(
        name="Calculate Benefit Term Date",
        uses=[
            "frame",
            "idi_benefit_period",
            "elimination_period",
            "birth_dt",
            "policy_end_dt",
        ],
        impacts=["frame"],
    )
    def _calculate_termination_dt(self):
        """Calculate benefit termination date if active individual were to become disabled for each policy duration."""
        if self.idi_benefit_period[-1] == "M":  # pylint: disable=E1136
            months = int(self.idi_benefit_period[:-1])  # pylint: disable=E1136
            self.frame["TERMINATION_DT"] = (
                self.frame["DATE_BD"]
                + pd.DateOffset(days=self.elimination_period)
                + pd.DateOffset(months=months)
            )
        elif self.idi_benefit_period[:2] == "TO":  # pylint: disable=E1136
            self.frame["TERMINATION_DT"] = self.policy_end_dt
        elif self.idi_benefit_period == "LIFE":
            self.frame["TERMINATION_DT"] = pd.to_datetime(
                date(
                    year=self.birth_dt.year + 120,
                    month=self.birth_dt.month,
                    day=self.birth_dt.day,
                )
            )

    @step(
        name="Model Claim Cost",
        uses=["frame", "claim_cost_model",],
        impacts=["modeled_claim_cost"],
    )
    def _model_claim_cost(self):
        """Model claim cost for active live if policy holder were to become disabled for each policy duration"""

        # create records
        record_cols = ["policy_id", "incurred_dt", "valuation_dt", "termination_dt"]
        frame = self.frame[["DATE_BD", "TERMINATION_DT"]].assign(
            policy_id=self.policy_id,
            incurred_dt=lambda df: df.DATE_BD,
            valuation_dt=lambda df: df.DATE_BD,
            termination_dt=lambda df: df.TERMINATION_DT,
        )[record_cols]
        records = convert_to_records(frame)

        # model disabled lives
        kwargs = {
            kw: getattr(self, kw)
            for kw in self.claim_cost_model.constant_params
            if kw not in record_cols + ["claim_id", "idi_diagnosis_grp"]
        }
        success, errors = self.claim_cost_model(
            records=records, claim_id="NA", idi_diagnosis_grp="AG", **kwargs,
        )
        if len(errors) == 0:
            self.modeled_claim_cost = {y: val for y, val in enumerate(success, start=1)}
        else:
            raise ModelRunError(str(errors))

    @step(
        name="Get Incidence Rate",
        uses=[
            "idi_contract",
            "idi_occupation_class",
            "idi_market",
            "idi_benefit_period",
            "tobacco_usage",
            "elimination_period",
            "gender",
            "incidence_modifier",
        ],
        impacts=["incidence_rates"],
    )
    def _get_incidence_rate(self):
        """Get incidence rates and multiply by incidence sensitivity to form final rate."""
        self.incidence_rates = get_incidence_rates(
            assumption_set=self.assumption_set, model_object=self
        ).assign(
            INCIDENCE_MODIFIER=self.incidence_modifier,
            FINAL_INCIDENCE_RATE=lambda df: df.INCIDENCE_RATE * df.INCIDENCE_MODIFIER,
        )

    @step(
        name="Get Withdraw Rates",
        uses=["assumption_set", "withdraw_table", "withdraw_modifier"],
        impacts=["withdraw_rates"],
    )
    def _get_withdraw_rates(self):
        """Get withdraw rates and multiply by incidence sensitivity to form final rate."""
        self.withdraw_rates = get_withdraw_rates(
            assumption_set=self.assumption_set,
            table_name=self.withdraw_table,
            gender=self.gender,
        ).assign(
            WITHDRAW_MODIFIER=self.withdraw_modifier,
            FINAL_WITHDRAW_RATE=lambda df: df.WITHDRAW_RATE * df.WITHDRAW_MODIFIER,
        )

    @step(
        name="Calculate Premiums",
        uses=["frame", "gross_premium", "gross_premium_freq"],
        impacts=["frame"],
    )
    def _calculate_premiums(self):
        if self.gross_premium_freq == "MONTH" or self.gross_premium_freq == "M":
            premium = self.gross_premium * 12
        elif self.gross_premium_freq == "QUARTER" or self.gross_premium_freq == "Q":
            premium = self.gross_premium * 4
        elif self.gross_premium_freq == "SEMIANNUAL" or self.gross_premium_freq == "S":
            premium = self.gross_premium * 2
        elif self.gross_premium_freq == "ANNUAL" or self.gross_premium_freq == "A":
            premium = self.gross_premium
        else:
            msg = "The value for gross_premium_freq is not an available option. "
            msg += "The value must be 'MONTH' / 'M', 'QUARTER' / 'Q', "
            msg += "'SEMIANNUAL' / 'S', or 'ANNUAL' / 'A'."
            raise ValueError(msg)

        self.frame["GROSS_PREMIUM"] = premium

    @step(
        name="Calculate Benefit Cost",
        uses=["frame", "modeled_claim_cost", "incidence_rates"],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate benefit cost by multiplying disabled claim cost by final incidence rate."""
        # merge final incidence rate
        self.frame = self.frame.merge(
            self.incidence_rates[["AGE_ATTAINED", "FINAL_INCIDENCE_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
        )

        # add modeled claim cost (i.e., DLR)
        self.frame["DLR"] = [df["DLR"].iat[0] for df in self.modeled_claim_cost.values()]

        # calculate benefit cost
        self.frame["BENEFIT_COST"] = (
            self.frame["DLR"] * self.frame["FINAL_INCIDENCE_RATE"]
        )

    @step(name="Calculate Lives", uses=["frame", "withdraw_rates"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate the beginning, middle, and ending lives for each duration using withdraw rates."""
        # merge withdraw rates
        self.frame = self.frame.merge(
            self.withdraw_rates[["AGE_ATTAINED", "FINAL_WITHDRAW_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
        )

        # calculate lives
        lives_ed = calc_continuance(self.frame["FINAL_WITHDRAW_RATE"])
        lives_bd = lives_ed.shift(1, fill_value=1)
        lives_md = (lives_bd + lives_ed) / 2

        # assign lives to frame
        self.frame["LIVES_BD"] = lives_bd
        self.frame["LIVES_MD"] = lives_md
        self.frame["LIVES_ED"] = lives_ed

    @step(
        name="Calculate Discount Factors", uses=["frame"], impacts=["frame"],
    )
    def _calculate_discount(self):
        """Calculate beginning, middle, and ending discount factors for each duration."""
        base_int_rate = get_interest_rate(self.policy_start_dt)
        self.frame["INTEREST_RATE_BASE"] = base_int_rate
        self.frame["INTEREST_RATE_MODIFIER"] = self.interest_modifier
        self.frame["INTEREST_RATE"] = (
            self.frame["INTEREST_RATE_BASE"] * self.frame["INTEREST_RATE_MODIFIER"]
        )
        self.frame["DISCOUNT_BD"] = calc_discount(self.frame["INTEREST_RATE"], t_adj=0)
        self.frame["DISCOUNT_MD"] = calc_discount(self.frame["INTEREST_RATE"], t_adj=0.5)
        self.frame["DISCOUNT_ED"] = calc_discount(self.frame["INTEREST_RATE"])

    @step(
        name="Calculate Durational ALR",
        uses=["frame", "net_benefit_method"],
        impacts=["frame"],
    )
    def _calculate_durational_alr(self):
        """Calculate active life reserves (ALR) for each duration."""
        # calculate present value of future benefits
        benefit_cols = ["BENEFIT_COST", "LIVES_MD", "DISCOUNT_MD"]
        pvfb = calc_pv(self.frame[benefit_cols].prod(axis=1))

        # calculate present value of future premium
        premium_cols = ["GROSS_PREMIUM", "LIVES_BD", "DISCOUNT_BD"]
        pvfp = calc_pv(self.frame[premium_cols].prod(axis=1))

        # calculate present value of future net benefifts
        pvfnb = calc_pvfnb(pvfb, pvfp, net_benefit_method=self.net_benefit_method)

        # calculate alr at end of duration
        alr_bd = (
            (pvfb - pvfnb) / self.frame["LIVES_BD"] / self.frame["DISCOUNT_BD"]
        ).clip(lower=0)

        # assign values to frame
        self.frame["PVFB"] = pvfb
        self.frame["PVFP"] = pvfp
        self.frame["PVFNB"] = pvfnb
        self.frame["ALR_BD"] = alr_bd
        self.frame["ALR_ED"] = alr_bd.shift(-1, fill_value=0)

    @step(
        name="Calculate Valuation Date ALR",
        uses=["frame", "valuation_dt"],
        impacts=["frame"],
    )
    def _calculate_valuation_dt_alr(self):
        """Calculate active life reserves (ALR) for each duration as of valuation date."""

        def alr_date(period):
            return self.valuation_dt + pd.DateOffset(years=period)

        # filter frame to valuation_dt starting in duration
        self.frame = self.frame[self.frame["DATE_ED"] >= self.valuation_dt].copy()

        # create projected alr date column
        self.frame["ALR_DATE"] = pd.to_datetime(
            [alr_date(period) for period in range(0, self.frame.shape[0])]
        )

        # calcualte interpolated alr
        self.frame["ALR"] = calc_interpolation(
            val_0=self.frame["ALR_BD"],
            val_1=self.frame["ALR_ED"],
            wt_0=self.frame["WT_BD"],
            wt_1=self.frame["WT_ED"],
            method="linear",
        ).round(2)

    @step(
        name="Create Output Frame",
        uses=[
            "frame",
            "policy_id",
            "model_version",
            "last_commit",
            "run_date_time",
            "coverage_id",
            "benefit_amount",
        ],
        impacts=["frame"],
    )
    def _to_output(self):
        """Reduce output to only needed columns."""
        self.frame = self.frame.assign(
            POLICY_ID=self.policy_id,
            MODEL_VERSION=self.model_version,
            LAST_COMMIT=self.last_commit,
            RUN_DATE_TIME=self.run_date_time,
            SOURCE=self.__class__.__qualname__,
            COVERAGE_ID=self.coverage_id,
            BENEFIT_AMOUNT=self.benefit_amount,
            # set column order
        )[list(ActiveLivesValOutput.columns)]


#########################################################################################
# Projection Policy Model - Base
#########################################################################################


@model
class AProjBasePMD(ALRBasePMD):
    pass
