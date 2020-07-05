import pandas as pd

from footings import create_parameter, use, create_model
from ..functions.generate_policies import (
    create_frame,
    sample_from_volume_tbl,
    add_benefit_amount,
    calculate_ages,
    calculate_dates,
    finalize_extract,
)

#########################################################################################
# arguments
#########################################################################################

arg_extract_type = create_parameter(
    name="extract_type",
    description="The type of extract to create.",
    dtype=str,
    allowed=["disabled-lives", "active-lives"],
)
arg_n = create_parameter(
    name="n", description="The number of simulated policies to create.", dtype=int
)
arg_volume_tbl = create_parameter(
    name="volume_tbl",
    description="""The volume table to use with refence to the distribution of policies \n
    by attributes.""",
    dtype=pd.DataFrame,
)
arg_as_of_dt = create_parameter(
    name="as_of_dt",
    description="The as of date which birth date will be based.",
    dtype=pd.Timestamp,
)
arg_seed = create_parameter(
    name="seed", description="The seed value to pass to numpy.random.", dtype=int
)

#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "create-frame",
        "function": create_frame,
        "args": {"n": arg_n, "extract_type": arg_extract_type,},
    },
    {
        "name": "sample-from-volume-tbl",
        "function": sample_from_volume_tbl,
        "args": {
            "frame": use("create-frame"),
            "volume_tbl": arg_volume_tbl,
            "seed": arg_seed,
        },
    },
    {
        "name": "add-benefit-amount",
        "function": add_benefit_amount,
        "args": {"frame": use("sample-from-volume-tbl")},
    },
    {
        "name": "calculate-ages",
        "function": calculate_ages,
        "args": {
            "frame": use("add-benefit-amount"),
            "extract_type": arg_extract_type,
            "seed": arg_seed,
        },
    },
    {
        "name": "calculate-dates",
        "function": calculate_dates,
        "args": {
            "frame": use("calculate-ages"),
            "as_of_dt": arg_as_of_dt,
            "extract_type": arg_extract_type,
        },
    },
    {
        "name": "finalize",
        "function": finalize_extract,
        "args": {"frame": use("calculate-dates"), "extract_type": arg_extract_type},
    },
]

#########################################################################################
# model
#########################################################################################

DESCRIPTION = "Create active or disabled life extracts."
extract_generator_model = create_model(
    name="ExtractGeneratorModel", description=DESCRIPTION, steps=steps
)
