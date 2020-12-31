from footings import model, def_meta
from .dlr_deterministic_base import ValDlrBasePM, STEPS


@model(steps=STEPS)
class ValDlrCatPRM(ValDlrBasePM):
    """The disabled life reserve (DLR) valuation model for the catastrophic (CAT) policy rider.

    This model is a child of the `ValDlrBasePM` with the only change being the model mode is
    changed from DLR to DLRCAT. This is to notify the model to calculate a different set of
    claim termination rates.
    """

    model_mode = def_meta(
        meta="DLRCAT",
        dtype=str,
        description="Mode used in CTR calculation as it varies whether policy is active or disabled.",
    )


@model
class ProjDlrCatPRM(ValDlrBasePM):
    pass
