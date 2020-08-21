import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec
from typing import Tuple

import pandas as pd
from dask import compute
from dask.delayed import delayed

from footings import define_parameter, use, build_model

from ..policy_models.alr_deterministic import (
    alr_deterministic_model,
    param_valuation_dt,
    param_assumption_set,
    param_net_benefit_method,
)
from ..functions.active_lives import OUTPUT_COLS
from .dispatch_model import dispatch_model_per_record

#########################################################################################
# arguments
#########################################################################################

# valuation_dt and assumption_set are imported from policy_models

param_base_extract = define_parameter(
    name="base_extract",
    description="""The active life base extract to use. See idi_model/schema/extract-active-lives-base.yaml for specification.""",
    dtype=pd.DataFrame,
)

param_rider_extract = define_parameter(
    name="rider_extract",
    description="""The active life rider extract to use. See idi_model/schema/extract-active-lives-riders.yaml for specification.""",
    dtype=pd.DataFrame,
)

param_model_type = define_parameter(
    name="model_type",
    description="""The policy model type to deploy. Options are :

        * `determinstic`
        * `stochastic`
    """,
    dtype=str,
    allowed=["deterministic", "stochastic"],
)

param_net_benefit_method = define_parameter(
    name="net_benefit_method",
    description="""The net benefit method to choose. Options are :

        * `PT1` = 1 year preliminary term
        * `PT2` = 2 year preliminary term
        * `NLP` = Net level premium
    """,
    dtype=str,
    allowed=["PT1", "PT2", "NLP"],
)

#########################################################################################
# functions
#########################################################################################


def check_extracts(
    base_extract: pd.DataFrame,
    rider_extract: pd.DataFrame,  # , valuation_dt: pd.Timestamp, schema: pd.DataFrame
):
    """Check extract against required schema.
    
    Parameters
    ----------
    extract : pd.DataFrame
        The extract to check.
    valuation_dt : pd.Timestamp
        The valuation date to be modeled.
    schema : 
        The required schema.
    
    Returns
    -------
    pd.DataFrame
        The extract.
    """
    return base_extract, rider_extract


def run_policy_model_per_record(
    extracts: Tuple[pd.DataFrame, pd.DataFrame],
    valuation_dt: pd.Timestamp,
    assumption_set: str,
    net_benefit_method: str,
    model_type: str,
) -> list:
    """Run each policy in extract through specified policy model.

    Parameters
    ----------
    extracts : Tuple[pd.DataFrame, pd.DataFrame]
        The base extract and rider extracts to run.
    valuation_dt : pd.Timestamp
        The valuation date to be modeled.
    assumption_set : str
        The assumptions set to model.
    net_benefit_method : str
        The net benefit method to use.
    model_type : callable
        The policy model to run for each policy in extract.

    Raises
    ------
    NotImplementedError
        When specifying policy_model = stochastic

    Returns
    -------
    list
        A list of all policies that have been ran through the policy model.
    """

    base_extract = extracts[0]
    base_extract.columns = [col.lower() for col in base_extract.columns]

    rider_extract = extracts[1]
    rider_extract.set_index(["POLICY_ID", "COVERAGE_ID"], inplace=True)

    records = []
    for base_key, base_record in base_extract.groupby(["policy_id", "coverage_id"]):
        try:
            rider_items = rider_extract.loc[base_key]
            rider_records = {
                k: v for k, v in zip(rider_items["PARAMETER"], rider_items["VALUE"])
            }
        except KeyError:
            rider_records = {}
        records.append(
            {**base_record.to_dict(orient="records")[0], **rider_records,}
        )

    return dispatch_model_per_record(
        records=records,
        policy_type="active",
        model_type=model_type,
        valuation_dt=valuation_dt,
        assumption_set=assumption_set,
        net_benefit_method=net_benefit_method,
    )


def create_output(results):
    """
    Creates model output.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        A tuple with three DataFrames : 
        
        * `[0]` = Time 0 reserve values
        * `[1]` = Projected reserve values
        * `[2]` = Any errors produced
    """
    successes = results[0]
    errors = results[1]
    time_0_cols = [
        "MODEL_VERSION",
        "LAST_COMMIT",
        "RUN_DATE_TIME",
        "POLICY_ID",
        "COVERAGE_ID",
        "ALR",
    ]
    try:
        time_0 = pd.concat([success.head(1) for success in successes]).reset_index(
            drop=True
        )
    except ValueError:
        time_0 = pd.DataFrame(columns=time_0_cols)
    try:
        projected = pd.concat(successes)
    except ValueError:
        projected = pd.DataFrame(columns=OUTPUT_COLS)

    return time_0[time_0_cols], projected, errors


#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "check-extracts",
        "function": check_extracts,
        "args": {
            "base_extract": param_base_extract,
            "rider_extract": param_rider_extract,
            # "valuation_dt": param_valuation_dt,
            # "schema": "123",
        },
    },
    {
        "name": "run-policy-model-per-record",
        "function": run_policy_model_per_record,
        "args": {
            "extracts": use("check-extracts"),
            "valuation_dt": param_valuation_dt,
            "assumption_set": param_assumption_set,
            "net_benefit_method": param_net_benefit_method,
            "model_type": param_model_type,
        },
    },
    {
        "name": "create-output",
        "function": create_output,
        "args": {"results": use("run-policy-model-per-record")},
    },
]

#########################################################################################
# models
#########################################################################################

DESCRIPTION = """Model to calculate active life reserves (ALRs) using the 2013 individual
disability insurance (IDI) valuation standard.

The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

The key assumptions underlying the model are -

* `Incidence Rates` - The probablility of an individual becoming disabled.
* `Termination Rates` - Given an an individual is disabled, the probability of an individual going off claim.

"""
active_lives_model = build_model(
    name="ActiveLivesModel", description=DESCRIPTION, steps=steps
)
