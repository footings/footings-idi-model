from footings import model, step
from footings.model_tools import frame_add_exposure
from .disabled_deterministic_base import DValBasePMD, STEPS


@model(steps=STEPS)
class DValColaRPMD(DValBasePMD):
    """The disabled life reserve (DLR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `DValBasePMD` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculate the benefit with cola less the original benefit amount.
    """

    @step(
        name="Calculate Monthly Benefits",
        uses=["frame", "cola_percent", "benefit_amount"],
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
        max_duration = self.frame[self.frame["AGE_ATTAINED"] == 65]["DURATION_YEAR"]
        if max_duration.size > 0:
            upper = max_duration.iat[0]
            power = self.frame["DURATION_YEAR"].clip(upper=upper)
        else:
            power = self.frame["DURATION_YEAR"]
        cola = (1 + self.cola_percent) ** (power - 1)
        self.frame["BENEFIT_AMOUNT"] = (
            self.frame["BENEFIT_FACTOR"]
            .mul(self.benefit_amount)
            .mul(cola)
            .sub(self.benefit_amount)
            .round(2)
        )


@model
class DProjColaRPMD(DValBasePMD):
    pass
