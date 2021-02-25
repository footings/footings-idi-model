from footings.model import def_intermediate, def_meta, model, step
from footings.model_tools import frame_add_exposure

from .disabled_deterministic_base import DValBasePMD

STEPS = [
    "_calculate_age_incurred",
    "_calculate_start_pay_dt",
    "_create_frame",
    "_calculate_age_attained",
    "_get_ctr_rates",
    "_get_sis_probability",
    "_calculate_benefit_cost",
    "_calculate_lives",
    "_calculate_discount",
    "_calculate_durational_dlr",
    "_calculate_valuation_dt_dlr",
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
    coverage_id = def_meta(
        meta="SIS",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    @step(name="Get SIS Probability", uses=[], impacts=["sis_probability"])
    def _get_sis_probability(self):
        """Get SIS probability."""
        self.sis_probability = 0.7

    @step(
        name="Calculate Monthly Benefits",
        uses=[
            "frame",
            "valuation_dt",
            "start_pay_dt",
            "termination_dt",
            "sis_probability",
            "benefit_amount",
        ],
        impacts=["frame"],
    )
    def _calculate_benefit_cost(self):
        """Calculate the monthly benefit amount for each duration."""
        self.frame = frame_add_exposure(
            self.frame,
            begin_date=max(self.valuation_dt, self.start_pay_dt),
            end_date=self.termination_dt,
            exposure_name="EXPOSURE",
            begin_duration_col="DATE_BD",
            end_duration_col="DATE_ED",
        )
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame["EXPOSURE"] * self.benefit_amount * (1 - self.sis_probability)
        ).round(2)


@model
class DProjSisRPMD(DValBasePMD):
    pass
