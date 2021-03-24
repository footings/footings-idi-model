from footings.data_dictionary import data_dictionary, def_column

#########################################################################################
# Disabled Lives Base Extract
#########################################################################################


@data_dictionary
class DisabledLivesBaseExtract:
    """Base policy extract for disabled lives. A unique record is represented by
    POLICY_ID + CLAIM_ID + COVERAGE_ID.
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
    """Rider policy extract for disabled lives. A unique record is represented by
    POLICY_ID + CLAIM_ID + COVERAGE_ID + RIDER_ATTRIBUTE.
    """

    POLICY_ID = DisabledLivesBaseExtract.def_column("POLICY_ID")
    CLAIM_ID = DisabledLivesBaseExtract.def_column("CLAIM_ID")
    COVERAGE_ID = DisabledLivesBaseExtract.def_column("COVERAGE_ID")
    RIDER_ATTRIBUTE = def_column(dtype="string", description="The rider attribute name.")
    VALUE = def_column(dtype="object", description="The value of the rider attribute.")
