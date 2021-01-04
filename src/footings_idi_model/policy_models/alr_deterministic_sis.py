from footings import model, def_meta
from .alr_deterministic_base import AValBasePM, STEPS
from .dlr_deterministic_sis import DValSisRPM, STEPS as CC_STEPS


@model(steps=CC_STEPS)
class _ActiveLifeSISClaimCostModel(DValSisRPM):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class AValSisRPM(AValBasePM):
    """The active life reserve (ALR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `AValBasePM` with the only changes being the addition
    of a step `_get_sis_probability` to lookup the probability of the policy holder
    qualifying for SIS (i.e., sis_probability) when modeling claim cost and the
    benefit amount is equal to the (1 - SIS prbability) x benefit amount.
    """

    claim_cost_model = def_meta(
        meta=_ActiveLifeSISClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
    )


@model
class AProjSisRPM(AValBasePM):
    pass
