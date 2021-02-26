from footings.actuarial_tools import frame_add_exposure
from footings.model import def_meta, def_parameter, model, step

from .disabled_deterministic_base import STEPS, DValBasePMD


@model(steps=STEPS)
class DValResRPMD(DValBasePMD):
    """The disabled life reserve (DLR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `DValBasePMD` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculates the benefit as the benefit amount x residual benefit percent.
    """

    residual_benefit_percent = def_parameter(
        dtype=float,
        description="The residual benefit percent to multiply by the benefit amount.",
    )
    coverage_id = def_meta(
        meta="RES",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )

    @step(
        name="Calculate Monthly Benefits",
        uses=[
            "frame",
            "valuation_dt",
            "start_pay_dt",
            "termination_dt",
            "residual_benefit_percent",
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
            self.frame["EXPOSURE"] * self.benefit_amount * self.residual_benefit_percent
        ).round(2)


@model
class DProjResRPMD(DValBasePMD):
    pass
