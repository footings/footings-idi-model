from copy import copy
import datetime

import numpy as np
import pandas as pd

from footings import (
    model,
    def_parameter,
    def_return,
    def_meta,
    step,
)

from ..attributes import (
    param_volume_tbl,
    param_n_simulations,
    param_seed,
    param_as_of_dt,
    meta_run_date_time,
    meta_model_version,
    meta_last_commit,
)
from ..schemas import active_lives_base_columns


def _calculate_age(frame: pd.DataFrame, low: float, high: float):
    return np.random.uniform(low=low, high=high, size=frame.shape[0])


def _birth_date_add_years(birth_dt: datetime.date, years: int):
    """Add years to birth date"""
    return pd.to_datetime(
        {
            "year": birth_dt.dt.year + years,
            "month": birth_dt.dt.month,
            "day": birth_dt.dt.day,
        }
    )


STEPS = [
    "_create_frame",
    "_sample_from_volume_tbl",
    "_add_premium_and_benefits",
    "_calculate_ages",
    "_calculate_dates",
    "_to_output_base_frame",
    "_create_rider_frame",
]


@model(steps=STEPS)
class GenerateALRExtracts:
    """Generate ALR Extracts"""

    n = param_n_simulations
    volume_tbl = param_volume_tbl
    as_of_dt = param_as_of_dt
    rop_rider_percent = def_parameter(
        dtype=float,
        min_val=0,
        max_val=1,
        description="The percent of policyholders with an ROP rider.",
    )
    seed = param_seed
    run_date_time = meta_run_date_time
    model_version = meta_model_version
    last_commit = meta_last_commit
    rop_return_freq_options = def_meta(
        meta=[7, 10],
        dtype=list,
        description="The return frequency options to be selected at random.",
    )
    rop_return_per_options = def_meta(
        meta=[0.5, 0.8],
        dtype=list,
        description="The return percentage options to be selected at random.",
    )
    rop_claims_paid_options = def_meta(
        meta=0, dtype=int, description="The claims paid to date."
    )
    base_frame = def_return(
        dtype=pd.DataFrame, description="The base extract that is being generated."
    )
    rider_frame = def_return(
        dtype=pd.DataFrame, description="The rider extract that is being generated."
    )

    @step(uses=["n"], impacts=["base_frame"])
    def _create_frame(self):
        """Create frame with n policies."""
        policy_ids = [f"M{i}" for i in range(1, self.n + 1)]
        self.base_frame = pd.DataFrame({"POLICY_ID": policy_ids, "COVERAGE_ID": "base"})

    @step(uses=["base_frame", "volume_tbl", "seed"], impacts=["base_frame"])
    def _sample_from_volume_tbl(self):
        """Sample from volume table."""
        np.random.seed(self.seed)
        frame = self.base_frame.copy()
        volume_tbl = copy(self.volume_tbl)
        frame["WT"] = np.random.uniform(size=frame.shape[0])
        cols = set(frame.columns)
        frame.reset_index(inplace=True)
        cols_added = set(frame.columns) - cols
        frame.sort_values(["WT"], inplace=True)
        total_wt = sum(volume_tbl["WT"])
        volume_tbl["WT"] = volume_tbl["WT"].cumsum() / total_wt
        frame = pd.merge_asof(frame, volume_tbl, on=["WT"]).drop(["WT"], axis=1)
        frame.sort_values(list(cols_added), inplace=True)
        self.base_frame = frame.drop(list(cols_added), axis=1).reset_index(drop=True)

    @step(uses=["base_frame"], impacts=["base_frame"])
    def _add_premium_and_benefits(self):
        """Add premium and benefits."""
        self.base_frame["GROSS_PREMIUM"] = 150.0
        self.base_frame["BENEFIT_AMOUNT"] = 100.0

    @step(uses=["base_frame", "seed"], impacts=["base_frame"])
    def _calculate_ages(self):
        """Calculate current age, incurred age, and termination age."""
        np.random.seed(self.seed)
        issue_age = _calculate_age(self.base_frame, 0.25, 0.6)
        self.base_frame["ISSUE_AGE"] = issue_age * 100
        self.base_frame["CURRENT_AGE"] = (
            _calculate_age(self.base_frame, issue_age, 0.62) * 100
        )

    @step(uses=["base_frame", "as_of_dt"], impacts=["base_frame"])
    def _calculate_dates(self):
        """Calculate birth date, incurred date, and termination date."""
        # calculate birth date
        days_from_birth = self.base_frame["CURRENT_AGE"].values * 365.25
        self.base_frame["BIRTH_DT"] = self.as_of_dt - pd.to_timedelta(
            days_from_birth, unit="D"
        ).round("D")

        # move any birth on leap year to the 28th
        leap_dts = (self.base_frame["BIRTH_DT"].dt.month == 2) & (
            self.base_frame["BIRTH_DT"].dt.day == 29
        )
        self.base_frame.loc[leap_dts, "BIRTH_DT"] = self.base_frame[leap_dts][
            "BIRTH_DT"
        ] - pd.offsets.Day(1)

        # calculate issue date
        days_from_issue = self.base_frame["ISSUE_AGE"].values * 365.25
        self.base_frame["POLICY_START_DT"] = self.base_frame[
            "BIRTH_DT"
        ] + pd.to_timedelta(days_from_issue, unit="D").round("D")

        # calculate termination date for benefits with monthly benefit period
        cond_list = [
            (self.base_frame["IDI_BENEFIT_PERIOD"].str[:2] != "TO").values,
            (self.base_frame["IDI_BENEFIT_PERIOD"].str[-2:] == "65").values,
            (self.base_frame["IDI_BENEFIT_PERIOD"].str[-2:] == "67").values,
            (self.base_frame["IDI_BENEFIT_PERIOD"].str[-2:] == "70").values,
        ]

        choice_list = [
            _birth_date_add_years(self.base_frame["BIRTH_DT"], 65).values.astype(str),
            _birth_date_add_years(self.base_frame["BIRTH_DT"], 65).values.astype(str),
            _birth_date_add_years(self.base_frame["BIRTH_DT"], 67).values.astype(str),
            _birth_date_add_years(self.base_frame["BIRTH_DT"], 70).values.astype(str),
        ]

        self.base_frame["POLICY_END_DT"] = pd.to_datetime(
            np.select(cond_list, choice_list)
        ) - pd.DateOffset(days=1)

        self.base_frame["PREMIUM_PAY_TO_DT"] = self.base_frame["POLICY_END_DT"]

    @step(uses=["base_frame"], impacts=["base_frame"])
    def _to_output_base_frame(self):
        """Reduce and order base frame to only needed columns"""
        self.base_frame = self.base_frame[active_lives_base_columns]

    @step(
        uses=["base_frame", "as_of_dt", "rop_rider_percent", "seed"],
        impacts=["rider_frame"],
    )
    def _create_rider_frame(self):
        """Create rider frame."""
        np.random.seed(seed=self.seed)
        self.rider_frame = self.base_frame.sample(
            frac=self.rop_rider_percent, random_state=self.seed
        )[["POLICY_ID"]]
        self.rider_frame["COVERAGE_ID"] = "rop"
        n_riders = self.rider_frame.shape[0]
        self.rider_frame["ROP_RETURN_FREQUENCY"] = np.random.choice(
            self.rop_return_freq_options, size=n_riders
        )
        self.rider_frame["ROP_RETURN_PERCENTAGE"] = np.random.choice(
            self.rop_return_per_options, size=n_riders
        )
        self.rider_frame["ROP_CLAIMS_PAID"] = 0
        self.rider_frame["ROP_FUTURE_CLAIMS_START_DT"] = self.as_of_dt.date()
        self.rider_frame = (
            self.rider_frame.melt(
                id_vars=["POLICY_ID", "COVERAGE_ID"],
                var_name="PARAMETER",
                value_name="VALUE",
            )
            .sort_values(by="POLICY_ID", axis=0, ignore_index=True)
            .reset_index(drop=True)
        )
