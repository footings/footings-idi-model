from footings import model, def_meta
from .alr_deterministic_base import ValAlrBasePBM, STEPS
from .dlr_deterministic_cola import ValDlrColaPRM, STEPS as CC_STEPS


@model(steps=CC_STEPS)
class _ActiveLifeCOLAClaimCostModel(ValDlrColaPRM):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class ValAlrColaPRM(ValAlrBasePBM):
    """The active life reserve (ALR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `ValAlrBasePBM` with the only change being how the monthly
    benefit is calculated. The base model uses the benefit amount passed while this model
    calculate the benefit with cola less the original benefit amount.
    """

    claim_cost_model = def_meta(
        meta=_ActiveLifeCOLAClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
    )


@model
class ProjAlrColaPRM(ValAlrBasePBM):
    pass
