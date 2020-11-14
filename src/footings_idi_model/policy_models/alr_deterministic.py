from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from functools import lru_cache
from inspect import getfullargspec

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
from footings import dispatch_function
from footings.model_tools import create_frame, calculate_age

from .dlr_deterministic import DLRDeterministicPolicyModel
from .dlr_deterministic import STEPS as DLR_STEPS
from ..assumptions.get_withdraw_rates import get_withdraw_rates
from ..assumptions.get_incidence_rates import get_incidence_rates
from ..assumptions.stat_gaap.interest import get_interest_rate
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
)
from ..schemas import active_base_schema, active_rider_schema


@model(steps=DLR_STEPS)
class _ActiveLifeDLRModel(DLRDeterministicPolicyModel):
    mode = define_meta(meta="ALR", dtype=str, description="The model mode which is ALR.")


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


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
    "_create_frame",
    "_calculate_age_attained",
    "_calculate_termination_dt",
    "_get_withdraw_rates",
    "_calculate_lives",
    "_get_incidence_rate",
    "_merge_incidence_rate",
    "_model_disabled_lives",
    "_calculate_benefit_cost",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_pvfnb",
    "_calculate_alr",
    "_to_output",
]


@model(steps=STEPS)
class ALRDeterministicPolicyModel(Footing):
    """A policy model to calculate active life reserves (ALRs) using the 2013 individual
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
    cola_percent = define_parameter(**active_base_schema["cola_percent"])
    gross_premium = define_parameter(**active_base_schema["gross_premium"])
    benefit_amount = define_parameter(**active_base_schema["benefit_amount"])
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence
    withdraw_modifier = modifier_withdraw
    withdraw_table = param_withdraw_table
    withdraw_rates = define_placeholder(
        dtype=pd.DataFrame, description="The placholder for withdraw rates."
    )
    incidence_rates = define_placeholder(
        dtype=pd.DataFrame, description="The placholder for incidence rates."
    )
    modeled_disabled_lives = define_placeholder(
        dtype=pd.DataFrame, description="The placholder for modeled disabled lives."
    )
    frame = define_asset(
        dtype=pd.DataFrame, description="The reserve projection for an active life."
    )
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    @step(uses=["birth_dt", "policy_start_dt"], impacts=["age_issued"])
    def _calculate_age_issued(self):
        self.age_issued = calculate_age(self.birth_dt, self.policy_start_dt, method="ALB")

    @step(uses=["policy_start_dt", "policy_end_dt"], impacts=["frame"])
    def _create_frame(self):
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

    @step(uses=["frame", "birth_dt"], impacts=["frame"])
    def _calculate_age_attained(self):
        self.frame["AGE_ATTAINED"] = calculate_age(
            self.birth_dt, self.frame["DATE_BD"], method="ALB"
        )

    @step(
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
        """Calculate termination date of an active life by duration."""
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
        uses=["assumptions_set", "withdraw_table", "withdraw_modifier"],
        impacts=["withdraw_rates"],
    )
    def _get_withdraw_rates(self):
        self.withdraw_rates = get_withdraw_rates(
            assumption_set=self.assumption_set,
            table_name=self.withdraw_table,
            gender=self.gender,
        ).assign(
            WITHDRAW_MODIFIER=self.withdraw_modifier,
            FINAL_WITHDRAW_RATE=lambda df: df.WITHDRAW_RATE * df.WITHDRAW_MODIFIER,
        )

    @step(uses=["frame", "withdraw_rates"], impacts=["frame"])
    def _calculate_lives(self):
        """Calculate the begining, middle, and ending lives for each duration."""
        self.frame = self.frame.merge(
            self.withdraw_rates[["AGE_ATTAINED", "FINAL_WITHDRAW_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
        )
        self.frame["LIVES_ED"] = (1 - self.frame["FINAL_WITHDRAW_RATE"]).cumprod()
        self.frame["LIVES_BD"] = self.frame["LIVES_ED"].shift(1, fill_value=1)
        self.frame["LIVES_MD"] = self.frame[["LIVES_BD", "LIVES_ED"]].mean(axis=1)

    @step(
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
        self.incidence_rates = get_incidence_rates(
            assumption_set=self.assumption_set, model_object=self
        ).assign(
            INCIDENCE_MODIFIER=self.incidence_modifier,
            FINAL_INCIDENCE_RATE=lambda df: df.INCIDENCE_RATE * df.INCIDENCE_MODIFIER,
        )

    @step(uses=["frame", "incidence_rates"], impacts=["frame"])
    def _merge_incidence_rate(self):
        self.frame = self.frame.merge(
            self.incidence_rates[["AGE_ATTAINED", "FINAL_INCIDENCE_RATE"]],
            how="left",
            on=["AGE_ATTAINED"],
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
        """Model disabled life."""

        @lru_cache(maxsize=128)
        def dlr_model_cache(**kwargs):
            return _ActiveLifeDLRModel(**kwargs).run()

        frame = (
            self.frame[["DATE_BD", "TERMINATION_DT"]]
            .rename(columns={"DATE_BD": "INCURRED_DT"})
            .assign(VALUATION_DT=lambda df: df.INCURRED_DT)
        )
        frame.columns = [col.lower() for col in frame.columns]
        records = frame.to_dict(orient="records")
        results = (
            dlr_model_cache(
                assumption_set=self.assumption_set,
                policy_id=self.policy_id,
                claim_id="NA",
                gender=self.gender,
                birth_dt=self.birth_dt,
                elimination_period=self.elimination_period,
                idi_contract=self.idi_contract,
                idi_benefit_period=self.idi_benefit_period,
                idi_diagnosis_grp="AG",
                idi_occupation_class=self.idi_occupation_class,
                cola_percent=self.cola_percent,
                benefit_amount=self.benefit_amount,
                **record,
            )
            for record in records
        )
        self.modeled_disabled_lives = {
            (dur_year, bd, ed): result
            for dur_year, bd, ed, result in zip(
                self.frame["DURATION_YEAR"],
                self.frame["DATE_BD"],
                self.frame["DATE_ED"],
                results,
            )
        }

    @step(uses=["frame", "modeled_disabled_lives"], impacts=["frame"])
    def _calculate_benefit_cost(self):
        dlrs = {k[0]: v["DLR"].iat[0] for k, v in self.modeled_disabled_lives.items()}
        self.frame["DLR"] = self.frame["DURATION_YEAR"].map(dlrs)
        self.frame["BENEFIT_COST"] = (
            self.frame["DLR"] * self.frame["FINAL_INCIDENCE_RATE"]
        ).round(2)

    @step(uses=["frame", "policy_start_dt", "interest_modifier"], impacts=["frame"])
    def _calculate_discount(self):
        """ """
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

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_pvfb(self):
        self.frame["PVFB"] = (
            self.frame[["LIVES_MD", "DISCOUNT_MD", "BENEFIT_COST"]]
            .prod(axis=1)
            .iloc[::-1]
            .cumsum()
            .round(2)
        )

    @step(uses=["frame", "net_benefit_method"], impacts=["frame"])
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

    @step(uses=["frame", "valuation_dt"], impacts=["frame"])
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

        dur_n_days = (self.frame["DATE_ED"].iat[0] - self.frame["DATE_BD"].iat[0]).days
        self.frame["WT_BD"] = (
            self.frame["DATE_ED"].iat[0] - self.valuation_dt
        ).days / dur_n_days
        self.frame["WT_ED"] = 1 - self.frame["WT_BD"]

        alr_bd, alr_ed = ["WT_BD", "ALR_BD"], ["WT_ED", "ALR_ED"]
        self.frame["ALR"] = (
            self.frame[alr_bd].prod(axis=1) + self.frame[alr_ed].prod(axis=1)
        ).round(2)

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Return the calculated frame with attributes covering the policy, duration, and ALR."""
        self.frame = self.frame.assign(
            POLICY_ID=self.policy_id,
            MODEL_VERSION=self.model_version,
            LAST_COMMIT=self.last_commit,
            RUN_DATE_TIME=self.run_date_time,
            COVERAGE_ID=self.coverage_id,
            BENEFIT_AMOUNT=self.benefit_amount,
        )[OUTPUT_COLS]
