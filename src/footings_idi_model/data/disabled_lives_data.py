from footings.data_dictionary import data_dictionary, def_column

from .shared import SharedOutputTerms

#########################################################################################
# Input Data Dictionaries
#########################################################################################


@data_dictionary
class DisabledLivesBaseExtract:
    """
    Base policy extract for disabled lives. A unique record is represented by POLICY_ID + CLAIM_ID + COVERAGE_ID.
    """

    POLICY_ID = def_column(
        dtype="string", description="The policy ID of the disabled claimant."
    )
    CLAIM_ID = def_column(
        dtype="string", description="The claim ID of the disabled claimant."
    )
    COVERAGE_ID = def_column(
        dtype="string", description="The coverage ID of the disabled claimant."
    )
    BIRTH_DT = def_column(
        dtype="datetime64[ns]", description="The birth date of the disabled claimant."
    )
    GENDER = def_column(
        dtype="string", description="The gender of the disabled claimant."
    )
    TOBACCO_USAGE = def_column(
        dtype="Bool", description="The tabacco usage of the disabled claimant."
    )
    INCURRED_DT = def_column(
        dtype="datetime64[ns]",
        description="The date of disablement for the claimant (i.e., the disablement date).",
    )
    TERMINATION_DT = def_column(
        dtype="datetime64[ns]",
        description="The termination date of the disabled claimant (i.e., the date benefits will stop being paid).",
    )
    ELIMINATION_PERIOD = def_column(
        dtype="int",
        description="The elimination days before benefits are paid for the disabled claimant.",
    )
    BENEFIT_AMOUNT = def_column(
        dtype="float16", description="The benefit amount for the disabled claimant."
    )
    IDI_OCCUPATION_CLASS = def_column(
        dtype="string", description="The IDI occupation class of the disabled claimant."
    )
    IDI_CONTRACT = def_column(
        dtype="string", description="The IDI contract type of the disabled claimant."
    )
    IDI_BENEFIT_PERIOD = def_column(
        dtype="string", description="The IDI benefit period for the disabled claimant."
    )
    IDI_MARKET = def_column(
        dtype="string", description="The IDI market for the disabled claimant."
    )
    IDI_DIAGNOSIS_GRP = def_column(
        dtype="string", description="The IDI diagnosis group of the disabled claimant."
    )
    COLA_PERCENT = def_column(
        dtype="float16",
        description="The COLA percent for the disabled claimant (0 if no COLA provided).",
    )


@data_dictionary
class DisabledLivesRiderExtract:
    """
    Rider policy extract for disabled lives. A unique record is represented by POLICY_ID + CLAIM_ID + COVERAGE_ID
    + RIDER_ATTRIBUTE.
    """

    POLICY_ID = DisabledLivesBaseExtract.def_column("POLICY_ID")
    CLAIM_ID = DisabledLivesBaseExtract.def_column("CLAIM_ID")
    COVERAGE_ID = DisabledLivesBaseExtract.def_column("COVERAGE_ID")
    RIDER_ATTRIBUTE = def_column(dtype="string", description="The rider attribute name.")
    VALUE = def_column(dtype="object", description="The value of the rider attribute.")


#########################################################################################
# Output Data Dictionaries
#########################################################################################


@data_dictionary
class DisabledLivesValOutput:
    """Disabled lives valuation output."""

    MODEL_VERSION = SharedOutputTerms.def_column("MODEL_VERSION")
    LAST_COMMIT = SharedOutputTerms.def_column("LAST_COMMIT")
    RUN_DATE_TIME = SharedOutputTerms.def_column("RUN_DATE_TIME")
    SOURCE = SharedOutputTerms.def_column("SOURCE")
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
    FINAL_CTR = def_column(
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


@data_dictionary
class DisabledLivesProjOutput:
    pass


"""

name: Disabled Lives Extract
enfore_strict: True
nullable: False
columns:
  - name: POLICY_ID
    dtype: str
    description: The policy ID of the disabled claimant.

  - name: BIRTH_DT
    dtype: date
    description: The birth date of the disabled claimant.

  - name: GENDER
    dtype: str
    description: The gender of the disabled claimant.
    allowed: [M, F]

  - name: TOBACCO_USAGE
    dtype: bool
    description: The tabacco usage of the disabled claimant.

  - name: CLAIM_ID
    dtype: str
    description: The claim ID of the disabled claimant.

  - name: COVERAGE_ID
    dtype: str
    description: The coverage ID of the disabled claimant.
    allowed: [BASE, CAT, COLA, RES, SIS, STOCHASTIC]

  - name: INCURRED_DT
    dtype: date
    description: The date of disablement for the claimant (i.e., the disablement date).

  - name: TERMINATION_DT
    dtype: date
    description: The termination date of the disabled claimant (i.e., the date benefits will stop being paid).

  - name: ELIMINATION_PERIOD
    dtype: int
    description: The elimination days before benefits are paid for the disabled claimant.
    allowed: [0, 7, 14, 30, 60, 90, 180, 360, 720]

  - name: BENEFIT_AMOUNT
    dtype: float
    description: The benefit amount for the disabled claimant.

  - name: IDI_OCCUPATION_CLASS
    dtype: str
    description: The IDI occupation class of the disabled claimant.
    allowed: ["1", "2", "3", "4", "M"]

  - name: IDI_CONTRACT
    dtype: str
    description: The IDI contract type of the disabled claimant.
    allowed: [AS, AO, SO, OE, KP]

  - name: IDI_BENEFIT_PERIOD
    dtype: str
    description: The IDI benefit period for the disabled claimant.
    allowed: [TO65, TO67, TO70, LIFE, 6M, 12M, 18M, 24M, 30M, 60M]

  - name: IDI_MARKET
    dtype: str
    description: The IDI market for the disabled claimant.
    allowed: [INDV, ES_IU, ES_VGSI, ES_MGSI]

  - name: IDI_DIAGNOSIS_GRP
    dtype: str
    description: The IDI diagnosis group of the disabled claimant.
    allowed: [VERY_LOW, LOW, MID, HIGH, VERY_HIGH, AG]

  - name: COLA_PERCENT
    dtype: float
    description: The COLA percent for the disabled claimant (0 if no COLA provided).


title: Disabled Lives Rider Extract
description: This is the data dictonary for the disabled lives rider extract. A unique record is
  represented by the POLICY_ID + CLAIM_ID + COVERAGE_ID.
columns:
  POLICY_ID:
    description: The policy ID of the disabled claimant.
    pandas_dtype: STRING
    nullable: false
  CLAIM_ID:
    description: The claim ID of the disabled claimant.
    pandas_dtype: STRING
    nullable: false
  COVERAGE_ID:
    description: The coverage ID of the disabled claimant.
    pandas_dtype: STRING
    checks:
      isin: [BASE, CAT, COLA, RES, SIS, STOCHASTIC]
    nullable: false
  RIDER_ATTRIBUTE:
    description: The rider attribute name.
    pandas_dtype: STRING
    checks:
      isin: [residual_benefit_percent]
    nullable: false
  VALUE:
    description: The value of the rider attribute.
    pandas_dtype: Object
    nullable: false
  index: null
  strict: true
"""
