import pandas as pd

from footings import define_parameter, use, build_model
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

param_extract_type = define_parameter(
    name="extract_type",
    description="The type of extract to create.",
    dtype=str,
    allowed=["disabled-lives", "active-lives"],
)
param_n = define_parameter(
    name="n", description="The number of simulated policies to create.", dtype=int
)
param_volume_tbl = define_parameter(
    name="volume_tbl",
    description="""The volume table to use with refence to the distribution of policies \n
    by attributes.""",
    dtype=pd.DataFrame,
)
param_as_of_dt = define_parameter(
    name="as_of_dt",
    description="The as of date which birth date will be based.",
    dtype=pd.Timestamp,
)
param_seed = define_parameter(
    name="seed", description="The seed value to pass to numpy.random.", dtype=int
)

#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "create-frame",
        "function": create_frame,
        "args": {"n": param_n, "extract_type": param_extract_type,},
    },
    {
        "name": "sample-from-volume-tbl",
        "function": sample_from_volume_tbl,
        "args": {
            "frame": use("create-frame"),
            "volume_tbl": param_volume_tbl,
            "seed": param_seed,
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
            "extract_type": param_extract_type,
            "seed": param_seed,
        },
    },
    {
        "name": "calculate-dates",
        "function": calculate_dates,
        "args": {
            "frame": use("calculate-ages"),
            "as_of_dt": param_as_of_dt,
            "extract_type": param_extract_type,
        },
    },
    {
        "name": "finalize",
        "function": finalize_extract,
        "args": {"frame": use("calculate-dates"), "extract_type": param_extract_type},
    },
]

#########################################################################################
# model
#########################################################################################

DESCRIPTION = "Create active or disabled life extracts."
extract_generator_model = build_model(
    name="ExtractGeneratorModel", description=DESCRIPTION, steps=steps
)
