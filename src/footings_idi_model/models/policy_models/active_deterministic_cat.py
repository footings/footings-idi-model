from inspect import getfullargspec

from footings.jigs import create_foreach_jig
from footings.model import def_meta, model

from .active_deterministic_base import STEPS, AValBasePMD
from .disabled_deterministic_cat import STEPS as CC_STEPS
from .disabled_deterministic_cat import DValCatRPMD

#########################################################################################
# Prepare Claim Cost Model - CAT Rider
#########################################################################################


@model(steps=CC_STEPS)
class ActiveLifeCATClaimCostModel(DValCatRPMD):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALRCAT",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


def _constant_params():
    kwargs = getfullargspec(ActiveLifeCATClaimCostModel).kwonlyargs
    kwargs.remove("incurred_dt")
    kwargs.remove("valuation_dt")
    return tuple(kwargs)


claim_cost_model = create_foreach_jig(
    ActiveLifeCATClaimCostModel,
    iterator_name="records",
    iterator_keys=("policy_id", "valuation_dt",),
    pass_iterator_keys=("policy_id", "valuation_dt",),
    constant_params=_constant_params(),
)


#########################################################################################
# Valuation Policy Model - CAT Rider
#########################################################################################


@model(steps=STEPS)
class AValCatRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the catastrophic (CAT) policy rider.

    This model is a child of the `AValBasePMD` with the only change being the model mode is
    changed from ALR to ALRCAT. This is to notify the model to calculate a different set of
    claim termination rates.
    """

    claim_cost_model = def_meta(
        meta=claim_cost_model, dtype=callable, description="The claim cost model used.",
    )
    coverage_id = def_meta(
        meta="CAT",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )


@model
class AProjCatRPMD(AValBasePMD):
    pass
