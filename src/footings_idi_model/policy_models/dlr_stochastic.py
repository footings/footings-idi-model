import pandas as pd
import numpy as np

from footings import model, step

from ..assumptions.stat_gaap.interest import get_interest_rate
from ..attributes import param_n_simulations, param_seed
from .dlr_deterministic_base import DValBasePM

OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "POLICY_ID",
    "RUN",
    "DATE_BD",
    "DATE_ED",
    "DURATION_YEAR",
    "DURATION_MONTH",
    "BENEFIT_AMOUNT",
    "FINAL_CTR",
    "BENEFITS_PAID",
    "DISCOUNT_VD",
    "PVFB_VD",
]

STEPS = [
    "_calculate_age_incurred",
    "_calculate_start_pay_date",
    "_create_frame",
    # "_calculate_cola_adjustment",
    "_calculate_monthly_benefits",
    "_calculate_discount",
    "_get_ctr_table",
    "_merge_ctr",
    "_simulate_payments",
    "_to_output",
]


@model(steps=STEPS)
class DLRStochasticPolicyModel(DValBasePM):
    """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual
    disability insurance (IDI) valuation standard.
    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.
    The key assumption underlying the model is -
    * `Termination Rates` - the probability of an individual going off claim.
    """

    seed = param_seed
    n_simulations = param_n_simulations

    @step(uses=["frame", "incurred_dt"], impacts=["frame"])
    def _calculate_discount(self):
        """Calculate beginning, middle, and ending discount factor for each duration."""
        interest_rate = get_interest_rate(self.incurred_dt)
        self.frame["DISCOUNT_VD"] = 1 / (1 + interest_rate) ** (
            (self.frame["DATE_ED"] - self.valuation_dt).dt.days / 365.25
        )

    @step(uses=["frame", "ctr_table"], impacts=["frame"])
    def _merge_ctr(self):
        self.frame = self.frame.merge(
            self.ctr_table[["DURATION_MONTH", "FINAL_CTR"]],
            how="left",
            on=["DURATION_MONTH"],
        )

    @step(uses=["frame", "seed", "n_simulations"], impacts=["frame"])
    def _simulate_payments(self):
        """Simulate lives."""
        np.random.seed(seed=self.seed)
        cols = list(self.frame.columns)
        cols_add = [
            "RANDOM",
            "TEMP_INFORCE",
            "INFORCE",
            "BENEFITS_PAID",
            "PVFB_VD",
        ]

        def simulate(df, run):
            rows = df.shape[0]
            df = df.copy()
            df["RUN"] = run
            df["RANDOM"] = np.random.uniform(size=rows)
            df["TEMP_INFORCE"] = np.select(
                [df["FINAL_CTR"] > df["RANDOM"]], [0], default=1.0
            )
            df["TEMP_CUM"] = df["TEMP_INFORCE"].cumsum()
            df.loc[(df["TEMP_CUM"] != df.index.values + 1), "TEMP_INFORCE"] = 0.0
            condlist = [(df["TEMP_INFORCE"].shift(1) == 1) & (df["TEMP_INFORCE"] == 0)]
            df["INFORCE"] = np.select(condlist, [0.5], default=df["TEMP_INFORCE"])
            df["BENEFITS_PAID"] = df["BENEFIT_AMOUNT"] * df["INFORCE"]
            df["PVFB_VD"] = (
                df[["BENEFITS_PAID", "DISCOUNT_VD"]]
                .prod(axis=1)
                .iloc[::-1]
                .cumsum()
                .round(2)
            )
            return df[["RUN"] + cols + cols_add]

        self.frame = pd.concat(
            [simulate(self.frame, n) for n in range(1, self.n_simulations + 1)]
        )

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Reduce output to only needed columns."""
        self.frame = self.frame.assign(
            POLICY_ID=self.policy_id,
            RUN_DATE_TIME=self.run_date_time,
            MODEL_VERSION=self.model_version,
            LAST_COMMIT=self.last_commit,
        )[OUTPUT_COLS]
