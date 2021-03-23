from footings.data_dictionary import data_dictionary, def_column

from ..extracts import DisabledLivesBaseExtract
from .shared import LAST_COMMIT, MODEL_VERSION, RUN_DATE_TIME, SOURCE

#########################################################################################
# Disabled Lives Valuation Output
#########################################################################################


@data_dictionary
class DisabledLivesValOutput:
    """Disabled lives valuation output."""

    MODEL_VERSION = MODEL_VERSION
    LAST_COMMIT = LAST_COMMIT
    RUN_DATE_TIME = RUN_DATE_TIME
    SOURCE = SOURCE
    POLICY_ID = DisabledLivesBaseExtract.def_column("POLICY_ID")
    CLAIM_ID = DisabledLivesBaseExtract.def_column("CLAIM_ID")
    COVERAGE_ID = DisabledLivesBaseExtract.def_column("COVERAGE_ID")
    DATE_BD = def_column(
        dtype="datetime64[ns]", description="Projected begining claim duration date."
    )
    DATE_ED = def_column(
        dtype="datetime64[ns]", description="Projected ending claim duration date."
    )
    DURATION_YEAR = def_column(dtype="int", description="Projected claim duration year.")
    DURATION_MONTH = def_column(
        dtype="int", description="Projected claim duration month."
    )
    BENEFIT_AMOUNT = def_column(dtype="float16", description="Projected benefit amount.")
    CTR = def_column(
        dtype="float16",
        description="Final claim termination rate with margin and sensitivites applied.",
    )
    LIVES_BD = def_column(
        dtype="float16",
        description="Projected average lives inforce begining claim duration.",
    )
    LIVES_MD = def_column(
        dtype="float16",
        description="Projected average lives inforce mid-point of claim duration.",
    )
    LIVES_ED = def_column(
        dtype="float16",
        description="Projected average lives inforce ending claim duration.",
    )
    DISCOUNT_BD = def_column(
        dtype="float16", description="Discount factor used begining claim duration."
    )
    DISCOUNT_MD = def_column(
        dtype="float16", description="Discount factor used mid-point of claim duration."
    )
    DISCOUNT_ED = def_column(
        dtype="float16", description="Discount factor used ending claim duration."
    )
    PVFB_BD = def_column(
        dtype="float16",
        description="Present value of future benefits begining claim duration.",
    )
    PVFB_ED = def_column(
        dtype="float16",
        description="Present value of future benefit ending claim duration.",
    )
    DATE_DLR = def_column(
        dtype="datetime64[ns]",
        description="Projected valuation dates using val date as base.",
    )
    DLR = def_column(
        dtype="float16",
        description="Projected DLR amount as of projected valuation date.",
    )
