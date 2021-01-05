from footings import model, step, def_intermediate
from footings.model_tools import frame_add_exposure
from .disabled_deterministic_base import DValBasePMD

STEPS = [
    "_calculate_age_incurred",
    "_calculate_start_pay_date",
    "_create_frame",
    "_calculate_vd_weights",
    "_get_ctr_table",
    "_calculate_lives",
    "_get_sis_probability",
    "_calculate_monthly_benefits",
    "_calculate_discount",
    "_calculate_pvfb",
    "_calculate_dlr",
    "_to_output",
]


@model(steps=STEPS)
class DValSisRPMD(DValBasePMD):
    """The disabled life reserve (DLR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `DValBasePMD` with the only changes being the addition
    of a step `_get_sis_probability` to lookup the probability of the policy holder
    qualifying for SIS (i.e., sis_probability) and the monthly benefit amount is equal
    to the (1 - SIS prbability) x benefit amount.
    """

    sis_probability = def_intermediate(
        dtype=float,
        description="The probability of policyholder qualifying for social insurance supplement benefit.",
    )

    @step(name="Get SIS Probability", uses=[], impacts=["sis_probability"])
    def _get_sis_probability(self):
        """Get SIS probability."""
        self.sis_probability = 0.7

    @step(
        name="Calculate Monthly Benefits",
        uses=["frame", "sis_probability", "benefit_amount"],
        impacts=["frame"],
    )
    def _calculate_monthly_benefits(self):
        """Calculate the monthly benefit amount for each duration."""
        self.frame = frame_add_exposure(
            self.frame,
            begin_date=max(self.valuation_dt, self.start_pay_date),
            end_date=self.termination_dt,
            exposure_name="BENEFIT_FACTOR",
            begin_duration_col="DATE_BD",
            end_duration_col="DATE_ED",
        )
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame["BENEFIT_FACTOR"]
            .mul(self.benefit_amount)
            .mul((1 - self.sis_probability))
            .round(2)
        )


@model
class DProjSisRPMD(DValBasePMD):
    pass
