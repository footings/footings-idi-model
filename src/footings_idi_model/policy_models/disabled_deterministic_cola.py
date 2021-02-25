from footings.model import def_meta, model, step
from footings.model_tools import frame_add_exposure

from .disabled_deterministic_base import STEPS, DValBasePMD


@model(steps=STEPS)
class DValColaRPMD(DValBasePMD):
    """The disabled life reserve (DLR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `DValBasePMD` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculate the benefit with cola less the original benefit amount.
    """

    coverage_id = def_meta(
        meta="COLA",
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
            "cola_percent",
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
        max_duration = self.frame[self.frame["AGE_ATTAINED"] == 65]["DURATION_YEAR"]
        if max_duration.size > 0:
            upper = max_duration.iat[0]
            power = self.frame["DURATION_YEAR"].clip(upper=upper)
        else:
            power = self.frame["DURATION_YEAR"]
        cola = (1 + self.cola_percent) ** (power - 1)
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame["EXPOSURE"] * ((self.benefit_amount * cola) - self.benefit_amount)
        ).round(2)


@model
class DProjColaRPMD(DValBasePMD):
    pass
