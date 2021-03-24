import numpy as np
from footings.model import def_meta, def_parameter, model, step

from .active_deterministic_base import AProjBasePMD, AValBasePMD

STEPS = [
    "_calculate_age_issued",
    "_create_frame",
    "_calculate_age_attained",
    "_calculate_termination_dt",
    "_get_mortality_rates",
    "_get_lapse_rates",
    "_calculate_premiums",
    "_calculate_benefit_cost",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_durational_alr",
    "_calculate_valuation_dt_alr",
    "_to_output",
]


def _calculate_rop_interval_premium(df):
    cum_prem = df.groupby(["ROP_INTERVAL"]).transform("cumsum")["GROSS_PREMIUM"]
    max_interval_dt = df.groupby(["ROP_INTERVAL"]).transform("max")["DATE_ED"]
    rop_premium = np.select([(max_interval_dt == df["DATE_ED"])], [cum_prem], default=0,)
    return rop_premium


@model(steps=STEPS)
class AValRopRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the return of premium (ROP)
    policy rider.

    This model is a child of the `AValBasePMD` and includes additional parameters for
    rop_return_freq, rop_return_percent and rop_claims_paid parameters.
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

    # meta
    coverage_id = def_meta(
        meta="ROP",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    @step(
        name="Calculate Benefit Cost",
        uses=["frame", "rop_return_freq", "rop_claims_paid", "rop_return_percent",],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate benefit cost for each duration."""

        # set payment intervals
        self.frame["INCIDENCE_RATE"] = 0
        self.frame["ROP_INTERVAL"] = (
            self.frame["DURATION_YEAR"].subtract(1).div(self.rop_return_freq).astype(int)
        )

        # add paid claims to frame
        self.frame["PAID_CLAIMS"] = 0
        rngs = self.frame.groupby(["ROP_INTERVAL"]).agg(
            START_DT=("DATE_BD", "first"), END_DT=("DATE_ED", "last")
        )
        end_dt = rngs.query("START_DT <= @self.valuation_dt <= END_DT")["END_DT"].iat[0]
        row = self.frame[self.frame["DATE_ED"] == end_dt].index[0]
        self.frame.at[row, "PAID_CLAIMS"] = self.rop_claims_paid

        # calculate expected total premium per ROP payment interval
        self.frame["ROP_PREMIUM"] = _calculate_rop_interval_premium(self.frame)

        # calculate ROP benefit cost
        self.frame["ROP_RETURN_PERCENTAGE"] = self.rop_return_percent
        self.frame["BENEFIT_COST"] = (
            self.frame["ROP_PREMIUM"] * self.frame["ROP_RETURN_PERCENTAGE"]
            - self.frame["PAID_CLAIMS"]
        ).clip(lower=0)


@model
class AProjRopRPMD(AProjBasePMD):
    pass
