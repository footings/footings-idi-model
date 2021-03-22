from footings.model import def_meta, model

from .disabled_deterministic_base import STEPS, DValBasePMD


@model(steps=STEPS)
class DValCatRPMD(DValBasePMD):
    """The disabled life reserve (DLR) valuation model for the catastrophic (CAT) policy rider.

    This model is a child of the `DValBasePMD` with the only change being the model mode is
    changed from DLR to DLRCAT. This is to notify the model to calculate a different set of
    claim termination rates.
    """

    model_mode = def_meta(
        meta="DLRCAT",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )
    coverage_id = def_meta(
        meta="CAT",
        dtype=str,
        description="The coverage id which recognizes base policy vs riders.",
    )


@model
class DProjCatRPMD(DValBasePMD):
    pass
