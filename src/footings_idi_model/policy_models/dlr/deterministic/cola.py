from footings import model, step
from .base import ValDLRBasePM, STEPS


@model(steps=STEPS)
class ValDLRCOLAPRM(ValDLRBasePM):
    """ """

    @step(name="Calculate Monthly Benefits", uses=[], impacts=[])
    def _calculate_monthly_benefits(self):
        pass


@model
class ProjDLRCOLAPRM(ValDLRBasePM):
    pass
