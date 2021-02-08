import pandas as pd
from footings.model import def_intermediate, def_meta, def_parameter, model, step
from footings.model_tools import frame_add_exposure

from .active_deterministic_base import AProjBasePMD, AValBasePMD

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
class AValRopRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the return of premium (ROP)
    policy rider.

    This model is a child of the `AValBasePMD` with a few changes -

    - The addition of rop_return_freq, rop_return_percent and rop_claims_paid parameters.
    - The addition of steps _calculate_rop_intervals, _calculate_rop_future_claims, and
        _calculate_rop_exp_payments steps which are used in the calculation of benefit cost.

    """

    # additional parameters
    rop_return_freq = def_parameter(
        dtype="int", description="The return of premium (ROP) frequency in years."
    )
    rop_return_percent = def_parameter(
        dtype="float", description="The return of premium (ROP) percentage."
    )
    rop_claims_paid = def_parameter(
        dtype="float", description="The return of premium (ROP) benefits paid."
    )
    rop_future_claims_start_dt = def_parameter(
        dtype="datetime64[ns]",
        description="The return of premium (ROP) benefits paid end date.",
    )

    # meta
    coverage_id = def_meta(
        meta="ROP",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    # intermediates
    rop_future_claims_frame = def_intermediate(dtype=pd.DataFrame, description="")
    rop_expected_claim_payments = def_intermediate(dtype=pd.DataFrame, description="")

    @step(
        name="Calculate ROP Payment Intervals",
        uses=["frame", "rop_return_freq"],
        impacts=["frame"],
    )
    def _calculate_rop_intervals(self):
        """Calculate return of premium (ROP) payment intervals."""
        self.frame["PAYMENT_INTERVAL"] = (
            self.frame["DURATION_YEAR"].subtract(1).div(self.rop_return_freq).astype(int)
        )

    @step(
        name="Model Future Claims",
        uses=["frame", "modeled_disabled_lives"],
        impacts=["rop_future_claims_frame"],
    )
    def _calculate_rop_future_claims(self):
        """Calculate future claims for return of premium (ROP) using the modeled disabled lives."""
        # max_payment_dates = (
        #     self.frame[["DURATION_YEAR", "PAYMENT_INTERVAL", "DATE_ED"]]
        #     .groupby(["PAYMENT_INTERVAL"], as_index=False)
        #     .transform(max)[["DATE_ED"]]
        #     .assign(DURATION_YEAR=self.frame["DURATION_YEAR"])
        #     .set_index(["DURATION_YEAR"])
        #     .to_dict()
        #     .get("DATE_ED")
        # )

        def model_payments(dur_year, frame):
            return (
                frame[["DATE_BD", "DATE_ED", "LIVES_MD", "BENEFIT_AMOUNT"]]
                .rename(columns={"LIVES_MD": "DISABLED_LIVES_MD"})
                .pipe(
                    frame_add_exposure,
                    begin_duration_col="DATE_BD",
                    end_duration_col="DATE_ED",
                    begin_date=self.rop_future_claims_start_dt,
                    exposure_name="EXPOSURE_FACTOR",
                )
                .assign(
                    ACTIVE_DURATION_YEAR=dur_year,
                    DISABLED_CLAIM_PAYMENTS=lambda df: df["EXPOSURE_FACTOR"]
                    * df["DISABLED_LIVES_MD"]
                    * df["BENEFIT_AMOUNT"],
                )
            )

        self.rop_future_claims_frame = pd.concat(
            [model_payments(k, v) for k, v in self.modeled_disabled_lives.items()]
        )

    @step(
        name="Calculate Expected Claims",
        uses=["frame", "rop_future_claims_frame"],
        impacts=["frame"],
    )
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
        name="Calculate Benefit Cost",
        uses=[
            "frame",
            "rop_claims_paid",
            "rop_return_percent",
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
        self.frame["RETURN_PERCENTAGE"] = self.rop_return_percent
        self.frame["BENEFIT_COST"] = (
            (
                self.frame["TOTAL_PREMIUM"] * self.frame["RETURN_PERCENTAGE"]
                - self.frame["EXPECTED_CLAIM_PAYMENTS"]
                - self.frame["CLAIMS_PAID"]
            )
            .clip(lower=0)
            .round(2)
        )


@model
class AProjRopRPMD(AProjBasePMD):
    pass
