from inspect import getfullargspec

from footings.jigs import create_foreach_jig
from footings.model import def_meta, model

from .active_deterministic_base import STEPS, AValBasePMD
from .disabled_deterministic_sis import STEPS as CC_STEPS
from .disabled_deterministic_sis import DValSisRPMD

#########################################################################################
# Prepare Claim Cost Model - SIS Rider
#########################################################################################


@model(steps=CC_STEPS)
class ActiveLifeSISClaimCostModel(DValSisRPMD):
    """Base model used to calculate claim cost for active lives."""

    model_mode = def_meta(
        meta="ALR",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


def _constant_params():
    kwargs = getfullargspec(ActiveLifeSISClaimCostModel).kwonlyargs
    kwargs.remove("incurred_dt")
    kwargs.remove("valuation_dt")
    return tuple(kwargs)


claim_cost_model = create_foreach_jig(
    ActiveLifeSISClaimCostModel,
    iterator_name="records",
    iterator_keys=("policy_id", "valuation_dt",),
    pass_iterator_keys=("policy_id", "valuation_dt",),
    constant_params=_constant_params(),
)


#########################################################################################
# Valuation Policy Model - SIS Rider
#########################################################################################


@model(steps=STEPS)
class AValSisRPMD(AValBasePMD):
    """The active life reserve (ALR) valuation model for the cost of living adjustment
    (COLA) policy rider.

    This model is a child of the `AValBasePMD` with the only changes being the addition
    of a step `_get_sis_probability` to lookup the probability of the policy holder
    qualifying for SIS (i.e., sis_probability) when modeling claim cost and the
    benefit amount is equal to the (1 - SIS prbability) x benefit amount.
    """

    claim_cost_model = def_meta(
        meta=claim_cost_model, dtype=callable, description="The claim cost model used.",
    )
    coverage_id = def_meta(
        meta="SIS",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )


@model
class AProjSisRPMD(AValBasePMD):
    pass
