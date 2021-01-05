from footings import model, def_parameter, def_meta
from .active_deterministic_base import AValBasePMD, STEPS
from .disabled_deterministic_res import DValResRPMD, STEPS as CC_STEPS


@model(steps=CC_STEPS)
class _ActiveLifeRESClaimCostModel(DValResRPMD):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class AValResRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `AValBasePMD` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculates the benefit as the benefit amount x residual benefit percent.
    """

    residual_benefit_percent = def_parameter(
        dtype=float,
        description="The residual benefit percent to multiply by the benefit amount.",
    )
    claim_cost_model = def_meta(
        meta=_ActiveLifeRESClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
    )


@model
class AProjResRPMD(AValBasePMD):
    pass
