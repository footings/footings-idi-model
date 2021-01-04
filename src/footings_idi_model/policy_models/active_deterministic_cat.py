from footings import model, def_meta
from .active_deterministic_base import AValBasePM, STEPS
from .disabled_deterministic_cat import DValCatRPM, STEPS as CC_STEPS


@model(steps=CC_STEPS)
class _ActiveLifeCATClaimCostModel(DValCatRPM):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALRCAT",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model(steps=STEPS)
class AValCatRPM(AValBasePM):
    """The active life reserve (ALR) valuation model for the catastrophic (CAT) policy rider.

    This model is a child of the `AValBasePM` with the only change being the model mode is
    changed from ALR to ALRCAT. This is to notify the model to calculate a different set of
    claim termination rates.
    """

    claim_cost_model = def_meta(
        meta=_ActiveLifeCATClaimCostModel,
        dtype=callable,
        description="The claim cost model used.",
    )


@model
class AProjCatRPM(AValBasePM):
    pass
