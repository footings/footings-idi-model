from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from functools import lru_cache
from inspect import getfullargspec

import numpy as np
import pandas as pd

from footings import (
    def_return,
    def_meta,
    def_sensitivity,
    def_parameter,
    def_intermediate,
    step,
    model,
)
from footings import dispatch_function
from footings.model_tools import create_frame, calculate_age

from .alr_deterministic import ALRDeterministicPolicyModel
from ..assumptions.get_withdraw_rates import get_withdraw_rates
from ..assumptions.get_incidence_rates import get_incidence_rates
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..schemas import active_base_schema, active_rider_schema


STEPS = [
    "_create_frame",
    "_calculate_age_attained",
    "_calculate_termination_dt",
    "_get_withdraw_rates",
    "_calculate_lives",
    "_get_incidence_rate",
    "_merge_incidence_rate",
    "_model_disabled_lives",
    "_calculate_rop_intervals",
    "_calculate_rop_future_claims",
    "_calculate_rop_exp_payments",
    "_calculate_benefit_cost",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_pvfnb",
    "_calculate_alr",
    "_to_output",
]


@model(steps=STEPS)
class ROPDeterministicPolicyModel(ALRDeterministicPolicyModel):
    """ """

    rop_return_frequency = def_parameter(**active_rider_schema["rop_return_frequency"])
    rop_return_percentage = def_parameter(**active_rider_schema["rop_return_percentage"])
    rop_claims_paid = def_parameter(**active_rider_schema["rop_claims_paid"])
    rop_future_claims_start_dt = def_parameter(
        **active_rider_schema["rop_future_claims_start_dt"]
    )
    rop_future_claims_frame = def_intermediate()
    rop_expected_claim_payments = def_intermediate()

    @step(uses=["frame", "rop_return_frequency"], impacts=["frame"])
    def _calculate_rop_intervals(self):
        """Calculate return of premium (ROP) payment intervals."""
        self.frame["PAYMENT_INTERVAL"] = (
            self.frame["DURATION_YEAR"]
            .subtract(1)
            .div(self.rop_return_frequency)
            .astype(int)
        )

    @step(uses=["frame", "modeled_disabled_lives"], impacts=["rop_future_claims_frame"])
    def _calculate_rop_future_claims(self):
        """Calculate future claims for return of premium (ROP).
        
        Using the modeled disabled lives, take each active modeled duration and filter the projected
        payments to be less than or equal to the last date of the ROP payment interval. The data is
        than concatenated into a single DataFrame.
        """
        max_payment_dates = (
            self.frame[["DURATION_YEAR", "PAYMENT_INTERVAL", "DATE_ED"]]
            .groupby(["PAYMENT_INTERVAL"], as_index=False)
            .transform(max)[["DATE_ED"]]
            .assign(DURATION_YEAR=self.frame["DURATION_YEAR"])
            .set_index(["DURATION_YEAR"])
            .to_dict()
            .get("DATE_ED")
        )

        def model_payments(dur_year, dur_start_dt, dur_end_dt, frame):
            cols = ["DATE_BD", "DATE_ED", "LIVES_MD", "BENEFIT_AMOUNT"]
            if dur_end_dt >= self.rop_future_claims_start_dt:
                if dur_start_dt >= self.rop_future_claims_start_dt:
                    exp_factor = 1.0
                else:
                    exp_factor = (self.rop_future_claims_start_dt - dur_start_dt) / (
                        dur_end_dt - dur_start_dt
                    )
            else:
                exp_factor = 0
            return (
                frame[frame.DATE_ED <= max_payment_dates.get(dur_year)][cols]
                .rename(columns={"LIVES_MD": "DISABLED_LIVES_MD"})
                .assign(
                    ACTIVE_DURATION_YEAR=dur_year,
                    EXPOSURE_FACTOR=exp_factor,
                    DISABLED_CLAIM_PAYMENTS=lambda df: df["EXPOSURE_FACTOR"]
                    * df["DISABLED_LIVES_MD"]
                    * df["BENEFIT_AMOUNT"],
                )
            )

        self.rop_future_claims_frame = pd.concat(
            [
                model_payments(k[0], k[1], k[2], v)
                for k, v in self.modeled_disabled_lives.items()
            ]
        )

    @step(uses=["frame", "rop_future_claims_frame"], impacts=["frame"])
    def _calculate_rop_exp_payments(self):
        """Calculate the expected claim payments for return of premium (ROP) for each active life duration."""
        base_cols = [
            "PAYMENT_INTERVAL",
            "DURATION_YEAR",
            "LIVES_MD",
            "FINAL_INCIDENCE_RATE",
        ]
        self.rop_expected_claim_payments = (
            self.rop_future_claims_frame.groupby(["ACTIVE_DURATION_YEAR"])
            .sum(["DISABLED_CLAIM_PAYMENTS"])
            .merge(
                self.frame[base_cols],
                how="right",
                right_on="DURATION_YEAR",
                left_on="ACTIVE_DURATION_YEAR",
            )
            .assign(
                EXPECTED_CLAIM_PAYMENTS=lambda df: df["FINAL_INCIDENCE_RATE"]
                * df["LIVES_MD"]
                * df["DISABLED_CLAIM_PAYMENTS"],
            )[base_cols + ["DISABLED_CLAIM_PAYMENTS", "EXPECTED_CLAIM_PAYMENTS"]]
        )

    @step(
        uses=[
            "frame",
            "rop_claims_paid",
            "rop_return_percentage",
            "rop_expected_claim_payments",
            "rop_future_claims_start_dt",
        ],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate benefit cost for each duration."""
        expected_claim_payments = (
            self.rop_expected_claim_payments.groupby(["PAYMENT_INTERVAL"])
            .sum(["EXPECTED_CLAIM_PAYMENTS"])
            .to_dict()
            .get("EXPECTED_CLAIM_PAYMENTS")
        )
        max_int_rows = (
            self.frame.groupby(["PAYMENT_INTERVAL"])["DURATION_YEAR"]
            .last()
            .sub(1)
            .astype(int)
        )
        self.frame["GROSS_PREMIUM"] = self.gross_premium
        self.frame["EXPECTED_CLAIM_PAYMENTS"] = 0
        self.frame.loc[max_int_rows, "EXPECTED_CLAIM_PAYMENTS"] = self.frame.loc[
            max_int_rows
        ]["PAYMENT_INTERVAL"].map(expected_claim_payments)
        criteria = (self.frame["DATE_BD"] <= self.rop_future_claims_start_dt) & (
            self.rop_future_claims_start_dt <= self.frame["DATE_ED"]
        )
        claim_row = self.frame[criteria]["PAYMENT_INTERVAL"]
        self.frame["CLAIMS_PAID"] = 0
        self.frame.loc[claim_row, "CLAIMS_PAID"] = self.rop_claims_paid
        total_premium = (
            self.frame.groupby(["PAYMENT_INTERVAL"])["GROSS_PREMIUM"].sum().to_dict()
        )
        self.frame["TOTAL_PREMIUM"] = 0
        self.frame.loc[max_int_rows, "TOTAL_PREMIUM"] = self.frame.loc[max_int_rows][
            "PAYMENT_INTERVAL"
        ].map(total_premium)
        self.frame["RETURN_PERCENTAGE"] = self.rop_return_percentage
        self.frame["BENEFIT_COST"] = (
            (
                self.frame["TOTAL_PREMIUM"] * self.frame["RETURN_PERCENTAGE"]
                - self.frame["EXPECTED_CLAIM_PAYMENTS"]
                - self.frame["CLAIMS_PAID"]
            )
            .clip(lower=0)
            .round(2)
        )
