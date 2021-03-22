from footings.data_dictionary import data_dictionary, def_column

#########################################################################################
# Active Lives Base Extract
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


#########################################################################################
# Active Lives Rider Extract
#########################################################################################


@data_dictionary
class ActiveLivesROPRiderExtract:
    """
    Rider policy extract for active lives. A unique record is represented by POLICY_ID + COVERAGE_ID + RIDER_ATTRIBUTE.
    """

    POLICY_ID = ActiveLivesBaseExtract.def_column("POLICY_ID")
    COVERAGE_ID = ActiveLivesBaseExtract.def_column("COVERAGE_ID")
    ROP_RETURN_FREQ = def_column(
        dtype="int", description="The ROP return frequency for the policy holder."
    )
    ROP_RETURN_PERCENT = def_column(
        dtype="float", description="The ROP return percent for the policy holder."
    )
    ROP_CLAIMS_PAID = def_column(
        dtype="float",
        description="The claims paid through ROP_FUTURE_CLAIMS_START_DT for the policy holder.",
    )
    ROP_FUTURE_CLAIMS_START_DT = def_column(
        dtype="datetime64[ns]",
        description="The date which to start modeling future expected claims.",
    )


#########################################################################################
# Disabled Lives Base Extract
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


#########################################################################################
# Disabled Lives Rider Extract
#########################################################################################


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
