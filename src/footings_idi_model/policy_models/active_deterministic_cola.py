from footings.model import def_meta, model

from .active_deterministic_base import STEPS, AValBasePMD
from .disabled_deterministic_cola import STEPS as CC_STEPS
from .disabled_deterministic_cola import DValColaRPMD


@model(steps=CC_STEPS)
class _ActiveLifeCOLAClaimCostModel(DValColaRPMD):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class AValColaRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `AValBasePMD` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculate the benefit with cola less the original benefit amount.
    """

    claim_cost_model = def_meta(
        meta=_ActiveLifeCOLAClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
    )
    coverage_id = def_meta(
        meta="COLA",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )


@model
class AProjColaRPMD(AValBasePMD):
    pass
