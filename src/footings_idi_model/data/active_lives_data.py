from footings.data_dictionary import data_dictionary, def_column
from .shared import SharedOutputTerms

#########################################################################################
# Input Data Dictionaries
#########################################################################################


@data_dictionary
class ActiveLivesBaseExtract:
    """
    Base policy extract for active lives. A unique record is represented by POLICY_ID + COVERAGE_ID.
    """

    POLICY_ID = def_column(
        dtype="string", description="The policy ID of the policy holder."
    )
    COVERAGE_ID = def_column(
        dtype="string", description="The coverage ID of the policy holder."
    )
    BIRTH_DT = def_column(
        dtype="datetime64[ns]", description="The birth date of the policy holder."
    )
    GENDER = def_column(dtype="string", description="The gender of the policy holder.")
    TOBACCO_USAGE = def_column(
        dtype="Bool", description="The tabacco usage of the policy holder."
    )
    POLICY_START_DT = def_column(
        dtype="datetime64[ns]",
        description="The date coverage starts for the policy issued.",
    )
    PREMIUM_PAY_TO_DT = def_column(
        dtype="datetime64[ns]",
        description="The date premium payments end for the policy issued.",
    )
    POLICY_END_DT = def_column(
        dtype="datetime64[ns]",
        description="The date coverage ends for the policy issued.",
    )
    ELIMINATION_PERIOD = def_column(
        dtype="int",
        description="The elimination days before benefits are paid for the policy holder.",
    )
    GROSS_PREMIUM = def_column(
        dtype="float", description="The policy gross premium amount."
    )
    GROSS_PREMIUM_FREQ = def_column(
        dtype="string", description="The frequency of premium payments."
    )
    BENEFIT_AMOUNT = def_column(
        dtype="float", description="The benefit amount for the policy holder."
    )
    IDI_OCCUPATION_CLASS = def_column(
        dtype="string", description="The IDI occupation class of the policy holder."
    )
    IDI_CONTRACT = def_column(
        dtype="string", description="The IDI contract type of the policy holder."
    )
    IDI_BENEFIT_PERIOD = def_column(
        dtype="string", description="The IDI benefit period for the policy holder."
    )
    IDI_MARKET = def_column(
        dtype="string", description="The IDI market for the policy holder."
    )
    COLA_PERCENT = def_column(
        dtype="float",
        description="The COLA percent for the policy holder (0 if no COLA provided).",
    )


@data_dictionary
class ActiveLivesRiderExtract:
    """
    Rider policy extract for active lives. A unique record is represented by POLICY_ID + COVERAGE_ID + RIDER_ATTRIBUTE.
    """

    POLICY_ID = ActiveLivesBaseExtract.def_column("POLICY_ID")
    COVERAGE_ID = ActiveLivesBaseExtract.def_column("COVERAGE_ID")
    RIDER_ATTRIBUTE = def_column(dtype="string", description="The rider attribute name.")
    VALUE = def_column(dtype="object", description="The value of the rider attribute.")


#########################################################################################
# Output Data Dictionaries
#########################################################################################


@data_dictionary
class ActiveLivesValOutput:
    """Active lives valuation output."""

    MODEL_VERSION = SharedOutputTerms.def_column("MODEL_VERSION")
    LAST_COMMIT = SharedOutputTerms.def_column("LAST_COMMIT")
    RUN_DATE_TIME = SharedOutputTerms.def_column("RUN_DATE_TIME")
    SOURCE = SharedOutputTerms.def_column("SOURCE")
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
    DATE_ALR = def_column(
        dtype="datetime64[ns]",
        description="Projected valuation dates using val date as base.",
    )
    ALR = def_column(
        dtype="float16",
        description="Projected ALR amount as of projected valuation date.",
    )


@data_dictionary
class ActiveLivesProjOutput:
    pass


"""

name: Active Lives Base Extract
enfore_strict: True
nullable: False
columns:
  - name: POLICY_ID
    dtype: str
    description: The policy ID of the policy holder.

  - name: BIRTH_DT
    dtype: date
    description: The birth date of the policy holder.

  - name: GENDER
    dtype: str
    description: The gender of the policy holder.
    allowed: [M, F]

  - name: TOBACCO_USAGE
    dtype: str
    description: The tabacco usage of the policy holder.
    allowed: [Y, N]

  - name: COVERAGE_ID
    dtype: str
    description: The coverage ID of the policy holder.
    allowed: [BASE, CAT, COLA, RES, ROP, SIS, WOP]

  - name: POLICY_START_DT
    dtype: date
    description: The date coverage starts for the policy issued.

  - name: PREMIUM_PAY_TO_DT
    dtype: date
    description: The date premium payments end for the policy issued.

  - name: POLICY_END_DT
    dtype: date
    description: The date coverage ends for the policy issued.

  - name: ELIMINATION_PERIOD
    dtype: int
    description: The elimination days before benefits are paid for the policy holder.
    allowed: [0, 7, 14, 30, 60, 90, 180, 360, 720]

  - name: GROSS_PREMIUM
    dtype: float
    description: The policy gross premium amount.

  - name: GROSS_PREMIUM_FREQ
    dtype: str
    description: The frequency of premium payments.
    allowed: [MONTH, QUARTER, SEMIANNUAL, ANNUAL]

  - name: BENEFIT_AMOUNT
    dtype: float
    description: The benefit amount for the policy holder.

  - name: IDI_OCCUPATION_CLASS
    dtype: str
    description: The IDI occupation class of the policy holder.
    allowed: ["1", "2", "3", "4", "M"]

  - name: IDI_CONTRACT
    dtype: str
    description: The IDI contract type of the policy holder.
    allowed: [AS, AO, SO, OE, KP]

  - name: IDI_BENEFIT_PERIOD
    dtype: str
    description: The IDI benefit period for the policy holder.
    allowed: [TO65, TO67, TO70, LIFE, 6M, 12M, 18M, 24M, 30M, 60M]

  - name: IDI_MARKET
    dtype: str
    description: The IDI market for the policy holder.
    allowed: [INDV, ES_IU, ES_VGSI, ES_MGSI]

  - name: COLA_PERCENT
    dtype: float
    description: The cost of living (COLA) percent for the policy holder (0 if no COLA provided).


name: Active Lives Rider Extract
enfore_strict: True
nullable: False
columns:
  - name: ROP_RETURN_FREQ
    dtype: int
    description: The return of premium (ROP) frequency in years.

  - name: ROP_RETURN_PERCENT
    dtype: float
    description: The return of premium (ROP) percentage.

  - name: ROP_CLAIMS_PAID
    dtype: float
    description: The return of premium (ROP) benefits paid.

  - name: ROP_FUTURE_CLAIMS_START_DT
    dtype: date
    description: The return of premium (ROP) benefits paid end date.
"""
