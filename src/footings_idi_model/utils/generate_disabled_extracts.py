from copy import copy

import numpy as np
import pandas as pd

from footings import (
    model,
    Footing,
    define_parameter,
    define_placeholder,
    define_asset,
    define_meta,
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
from ..schemas import disabled_life_columns


def _calculate_age(frame: pd.DataFrame, low: float, high: float):
    return np.random.uniform(low=low, high=high, size=frame.shape[0])


def _calculate_termination_age(frame: pd.DataFrame, base_age: int):
    # calculate termination age
    benefit_period = frame["IDI_BENEFIT_PERIOD"].values.astype(str)
    cond_list_1 = [np.char.endswith(benefit_period, "M")]
    choice_list_1 = [np.char.strip(benefit_period, "M")]
    years_add = np.select(cond_list_1, choice_list_1).astype(int) / 1200

    cond_list_2 = [
        np.char.find(benefit_period, "TO") >= 0,
        np.char.find(benefit_period, "LIFE") >= 0,
    ]
    choice_list_2 = [np.char.strip(benefit_period, "TO"), 120]
    end_year = np.select(cond_list_2, choice_list_2).astype(int) / 100

    cond_list_3 = [years_add > 0, end_year > 0]
    choice_list_3 = [base_age + years_add, end_year]
    return np.select(cond_list_3, choice_list_3)


STEPS = [
    "_create_frame",
    "_sample_from_volume_tbl",
    "_add_premium_and_benefits",
    "_calculate_ages",
    "_calculate_dates",
    "_to_output",
]


@model(steps=STEPS)
class GenerateDLRExtract(Footing):
    """Generate DLR Extract"""

    n = param_n_simulations
    volume_tbl = param_volume_tbl
    as_of_dt = param_as_of_dt
    seed = param_seed
    run_date_time = meta_run_date_time
    model_version = meta_model_version
    last_commit = meta_last_commit
    frame = define_asset(
        dtype=pd.DataFrame, description="The extract that is being generated."
    )

    @step(uses=["n"], impacts=["frame"])
    def _create_frame(self):
        """Create frame with n policies."""
        policy_ids = [f"M{i}" for i in range(1, self.n + 1)]
        claim_ids = [f"{p}C1" for p in policy_ids]
        self.frame = pd.DataFrame(
            {"POLICY_ID": policy_ids, "CLAIM_ID": claim_ids, "COVERAGE_ID": "base"}
        )

    @step(uses=["frame", "volume_tbl", "seed"], impacts=["frame"])
    def _sample_from_volume_tbl(self):
        """Sample from volume table."""
        np.random.seed(self.seed)
        frame = self.frame.copy()
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
        self.frame = frame.drop(list(cols_added), axis=1).reset_index(drop=True)

    @step(uses=["frame"], impacts=["frame"])
    def _add_premium_and_benefits(self):
        """Add premium and benefits."""
        self.frame["BENEFIT_AMOUNT"] = 100.0
        self.frame["PAID_TO_DT"] = pd.NA

    @step(uses=["frame", "seed"], impacts=["frame"])
    def _calculate_ages(self):
        """Calculate current age, incurred age, and termination age."""
        np.random.seed(self.seed)
        incurred_age = _calculate_age(self.frame, 0.25, 0.6)
        termination_age = _calculate_termination_age(self.frame, incurred_age)
        current_age = _calculate_age(self.frame, incurred_age, termination_age)
        self.frame["CURRENT_AGE"] = current_age * 100
        self.frame["INCURRED_AGE"] = incurred_age * 100
        self.frame["TERMINATION_AGE"] = termination_age * 100

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_dates(self):
        """Calculate birth date, incurred date, and termination date."""
        # calculate birth date
        days_from_birth = self.frame["CURRENT_AGE"].values * 365.25

        self.frame["BIRTH_DT"] = self.as_of_dt - pd.to_timedelta(
            days_from_birth, unit="D"
        ).round("D")

        # move any birth on leap year to the 28th
        leap_dts = (self.frame["BIRTH_DT"].dt.month == 2) & (
            self.frame["BIRTH_DT"].dt.day == 29
        )
        self.frame.loc[leap_dts, "BIRTH_DT"] = self.frame[leap_dts][
            "BIRTH_DT"
        ] - pd.offsets.Day(1)

        # calculate incurred date
        self.frame["INCURRED_DT"] = (
            self.frame["BIRTH_DT"]
            + pd.to_timedelta(self.frame["INCURRED_AGE"] * 365.25, unit="D")
        ).dt.round("D")

        term_dt = []
        for _, row in self.frame.iterrows():
            if row.IDI_BENEFIT_PERIOD[-1] == "M":
                mnt = int(row.IDI_BENEFIT_PERIOD.replace("M", ""))
                term_dt.append(
                    row.INCURRED_DT
                    + pd.DateOffset(days=row.ELIMINATION_PERIOD)
                    + pd.DateOffset(months=mnt)
                )
            else:
                if row.IDI_BENEFIT_PERIOD == "LIFE":
                    years = 120
                else:
                    years = int(row.IDI_BENEFIT_PERIOD.replace("TO", ""))
                term_dt.append(row.BIRTH_DT + pd.DateOffset(years=years))

        self.frame["TERMINATION_DT"] = pd.Series(term_dt) - pd.DateOffset(days=1)

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Filter to only needed columns."""
        self.frame = self.frame[disabled_life_columns]
