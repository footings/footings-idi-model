from datetime import date
from functools import lru_cache
from inspect import getfullargspec

import numpy as np
import pandas as pd

from footings import (
    model,
    step,
    def_meta,
    def_intermediate,
    def_return,
)
from footings.model_tools import create_frame, calculate_age, frame_add_weights

from .alr_base import ALRBasePM
from .dlr_deterministic_base import DValBasePM, STEPS as CC_STEPS
from ..assumptions.get_withdraw_rates import get_withdraw_rates
from ..assumptions.get_incidence_rates import get_incidence_rates
from ..assumptions.stat_gaap.interest import get_interest_rate


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "SOURCE",
    "POLICY_ID",
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
    "FINAL_INCIDENCE_RATE",
    "BENEFIT_COST",
    "PVFB",
    "PVFNB",
    "ALR_BD",
    "ALR_ED",
    "DATE_ALR",
    "ALR",
]


STEPS = [
    "_calculate_age_issued",
    "_create_frame",
    "_calculate_vd_weights",
    "_calculate_age_attained",
    "_calculate_termination_dt",
    "_get_withdraw_rates",
    "_merge_withdraw_rates",
    "_calculate_lives",
    "_get_incidence_rate",
    "_merge_incidence_rate",
    "_model_claim_cost",
    "_calculate_benefit_cost",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_pvfnb",
    "_calculate_alr",
    "_to_output",
]


@model(steps=CC_STEPS)
class _ActiveLifeBaseClaimCostModel(DValBasePM):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class AValBasePM(ALRBasePM):
    """The active life reserve (ALR) valuation model for the base policy."""

    # meta
    claim_cost_model = def_meta(
        meta=_ActiveLifeBaseClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
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
    modeled_disabled_lives = def_intermediate(
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
        fixed = {
            "frequency": "Y",
            "col_date_nm": "DATE_BD",
            "duration_year": "DURATION_YEAR",
        }
        self.frame = (
            create_frame(self.policy_start_dt, self.policy_end_dt, **fixed)
            .pipe(_assign_end_date)
            .query("DATE_BD <= @self.policy_end_dt")
        )[["DATE_BD", "DATE_ED", "DURATION_YEAR"]]

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
                    year=date.year(self.birth_dt) + 120,
                    month=date.month(self.birth_dt),
                    day=date.day(self.birth_dt),
                )
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
        name="Merge Withdraw Rates", uses=["frame", "withdraw_rates"], impacts=["frame"]
    )
    def _merge_withdraw_rates(self):
        """Merge withdraw rates into frame."""
        self.frame = self.frame.merge(
            self.withdraw_rates[["AGE_ATTAINED", "FINAL_WITHDRAW_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
        )

    @step(name="Calculate Lives", uses=["frame"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate the beginning, middle, and ending lives for each duration using withdraw rates."""
        self.frame["LIVES_ED"] = (1 - self.frame["FINAL_WITHDRAW_RATE"]).cumprod()
        self.frame["LIVES_BD"] = self.frame["LIVES_ED"].shift(1, fill_value=1)
        self.frame["LIVES_MD"] = self.frame[["LIVES_BD", "LIVES_ED"]].mean(axis=1)

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
        name="Merge Incidence Rate", uses=["frame", "incidence_rates"], impacts=["frame"]
    )
    def _merge_incidence_rate(self):
        """Merge incidence rates into frame."""
        self.frame = self.frame.merge(
            self.incidence_rates[["AGE_ATTAINED", "FINAL_INCIDENCE_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
        )

    @step(
        name="Model Claim Cost",
        uses=[
            "frame",
            "assumption_set",
            "birth_dt",
            "elimination_period",
            "idi_benefit_period",
            "cola_percent",
            "claim_cost_model",
        ],
        impacts=["modeled_disabled_lives"],
    )
    def _model_claim_cost(self):
        """Model claim cost for active live if policy holder were to become disabled for each policy duration"""

        @lru_cache(maxsize=256)
        def claim_cost_model(**kwargs):
            return self.claim_cost_model(**kwargs).run()

        model_args = getfullargspec(self.claim_cost_model).kwonlyargs
        exclude = [
            "claim_id",
            "idi_diagnosis_grp",
            "incurred_dt",
            "termination_dt",
            "valuation_dt",
        ]
        self_kws = {arg: getattr(self, arg) for arg in model_args if arg not in exclude}

        frame = (
            self.frame[["DATE_BD", "TERMINATION_DT"]]
            .rename(columns={"DATE_BD": "INCURRED_DT"})
            .assign(VALUATION_DT=lambda df: df.INCURRED_DT)
        )
        frame.columns = [col.lower() for col in frame.columns]
        records = frame.to_dict(orient="records")
        results = (
            claim_cost_model(claim_id="NA", idi_diagnosis_grp="AG", **self_kws, **record,)
            for record in records
        )
        self.modeled_disabled_lives = {
            int(dur_year): result
            for dur_year, result in zip(self.frame["DURATION_YEAR"], results)
        }

    @step(
        name="Calculate Benefit Cost",
        uses=["frame", "modeled_disabled_lives"],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate benefit cost by multiplying disabled claim cost by final incidence rate."""
        dlrs = {k: v["DLR"].iat[0] for k, v in self.modeled_disabled_lives.items()}
        self.frame["DLR"] = self.frame["DURATION_YEAR"].map(dlrs)
        self.frame["BENEFIT_COST"] = (
            self.frame["DLR"] * self.frame["FINAL_INCIDENCE_RATE"]
        ).round(2)

    @step(
        name="Calculate Discount Factors",
        uses=["frame", "policy_start_dt", "interest_modifier"],
        impacts=["frame"],
    )
    def _calculate_discount(self):
        """Calculate beginning, middle, and ending discount factors for each duration."""
        interest_rate = get_interest_rate(self.policy_start_dt) * self.interest_modifier
        self.frame["DISCOUNT_BD"] = 1 / (1 + interest_rate) ** (
            self.frame["DURATION_YEAR"] - 1
        )
        self.frame["DISCOUNT_MD"] = 1 / (1 + interest_rate) ** (
            self.frame["DURATION_YEAR"] - 0.5
        )
        self.frame["DISCOUNT_ED"] = 1 / (1 + interest_rate) ** (
            self.frame["DURATION_YEAR"]
        )

    @step(name="Calculate PVFB", uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        """Calculate present value of future benefits (PVFB)."""
        self.frame["PVFB"] = (
            self.frame[["LIVES_MD", "DISCOUNT_MD", "BENEFIT_COST"]]
            .prod(axis=1)
            .iloc[::-1]
            .cumsum()
            .round(2)
        )

    @step(name="Calculate PVNFB", uses=["frame", "net_benefit_method"], impacts=["frame"])
    def _calculate_pvfnb(self):
        """Calculate present value net future benefits (PVNFB)."""
        self.frame["PAY_FLAG"] = 1
        self.frame["PVP"] = (
            self.frame[["PAY_FLAG", "LIVES_BD", "DISCOUNT_BD"]]
            .prod(axis=1)
            .iloc[::-1]
            .cumsum()
        )
        pvp = self.frame["PVP"].iat[0]

        if self.net_benefit_method == "NLP":
            pvfb = self.frame["PVFB"].iat[0]
        elif self.net_benefit_method == "PT1":
            pvfb = self.frame[self.frame.DURATION_YEAR > 1]["PVFB"].iat[0]
        elif self.net_benefit_method == "PT2":
            pvfb = self.frame[self.frame.DURATION_YEAR > 2]["PVFB"].iat[0]
        else:
            msg = f"The net_benefit_method [{self.net_benefit_method}] is not recognzied. See Documentation."
            raise ValueError(msg)

        nlp = pvfb / pvp
        duration = self.frame["DURATION_YEAR"].values
        cond_list = [
            np.array((self.net_benefit_method == "PT1") & (duration <= 1), dtype=bool),
            np.array((self.net_benefit_method == "PT2") & (duration <= 2), dtype=bool),
        ]
        choice_list = [self.frame["PVFB"].values, self.frame["PVFB"].values]
        self.frame["PVFNB"] = np.select(
            cond_list, choice_list, default=(self.frame["PVP"].values * nlp)
        ).round(2)

    @step(name="Calculate ALR", uses=["frame", "valuation_dt"], impacts=["frame"])
    def _calculate_alr(self):
        """Calculate active life reserves (ALR) from issue."""
        self.frame["ALR_BD"] = (
            (self.frame["PVFB"] - self.frame["PVFNB"])
            .div(self.frame["DISCOUNT_BD"])
            .clip(lower=0)
        ).round(2)
        self.frame["ALR_ED"] = self.frame["ALR_BD"].shift(-1, fill_value=0)

        self.frame = self.frame[self.frame["DATE_ED"] >= self.valuation_dt].copy()
        self.frame["DATE_ALR"] = pd.to_datetime(
            [
                self.valuation_dt + pd.DateOffset(years=period)
                for period in range(0, self.frame.shape[0])
            ]
        )

        alr_bd, alr_ed = ["WT_BD", "ALR_BD"], ["WT_ED", "ALR_ED"]
        self.frame["ALR"] = (
            (self.frame[alr_bd].prod(axis=1) + self.frame[alr_ed].prod(axis=1))
            .round(2)
            .clip(lower=0)
        )

    @step(
        name="Create Output Frame",
        uses=[
            "frame",
            "policy_id",
            "model_version",
            "last_commit",
            "run_date_time",
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
            BENEFIT_AMOUNT=self.benefit_amount,
        )[OUTPUT_COLS]


@model
class AProjBasePM(ALRBasePM):
    pass
