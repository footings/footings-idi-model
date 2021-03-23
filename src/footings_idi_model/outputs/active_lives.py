from footings.data_dictionary import data_dictionary, def_column

from ..extracts import ActiveLivesBaseExtract
from .shared import LAST_COMMIT, MODEL_VERSION, RUN_DATE_TIME, SOURCE

#########################################################################################
# Active Lives Valuation Output
#########################################################################################


@data_dictionary
class ActiveLivesValOutput:
    """Active lives valuation output."""

    MODEL_VERSION = MODEL_VERSION
    LAST_COMMIT = LAST_COMMIT
    RUN_DATE_TIME = RUN_DATE_TIME
    SOURCE = SOURCE
    POLICY_ID = ActiveLivesBaseExtract.def_column("POLICY_ID")
    COVERAGE_ID = ActiveLivesBaseExtract.def_column("COVERAGE_ID")
    DATE_BD = def_column(
        dtype="datetime64[ns]", description="Projected begining policy duration date."
    )
    DATE_ED = def_column(
        dtype="datetime64[ns]", description="Projected ending policy duration date."
    )
    DURATION_YEAR = def_column(dtype="int", description="Projected policy duration year.")
    LIVES_BD = def_column(
        dtype="float16",
        description="Projected average lives inforce begining policy duration.",
    )
    LIVES_MD = def_column(
        dtype="float16",
        description="Projected average lives inforce mid-point of policy duration.",
    )
    LIVES_ED = def_column(
        dtype="float16",
        description="Projected average lives inforce ending policy duration.",
    )
    DISCOUNT_BD = def_column(
        dtype="float16", description="Discount factor used begining policy duration."
    )
    DISCOUNT_MD = def_column(
        dtype="float16", description="Discount factor used mid-point of policy duration."
    )
    DISCOUNT_ED = def_column(
        dtype="float16", description="Discount factor used ending policy duration."
    )
    BENEFIT_AMOUNT = def_column(dtype="float16", description="Projected benefit amount.")
    FINAL_INCIDENCE_RATE = def_column(
        dtype="float16",
        description="Final incidence rate with margin and sensitivites applied.",
    )
    BENEFIT_COST = def_column(
        dtype="float16",
        description="Projected benefit cost (PV future benefits x incidence rate).",
    )
    PVFB = def_column(dtype="float16", description="Present value of future benefits.",)
    PVFNB = def_column(
        dtype="float16", description="Present value of future bet benefits.",
    )
    ALR_BD = def_column(
        dtype="float16", description="Projected ALR amount at begining policy duration.",
    )
    ALR_ED = def_column(
        dtype="float16", description="Projected ALR amount at ending policy duration.",
    )
    ALR_DATE = def_column(
        dtype="datetime64[ns]",
        description="Projected valuation dates using val date as base.",
    )
    ALR = def_column(
        dtype="float16",
        description="Projected ALR amount as of projected valuation date.",
    )
