import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec

import pandas as pd
from dask import compute
from dask.delayed import delayed

from footings import create_argument, use, create_model

from ..policy_models.alr_deterministic import (
    alr_deterministic_model,
    arg_valuation_dt,
    arg_assumption_set,
    arg_net_benefit_method,
)

#########################################################################################
# arguments
#########################################################################################

# valuation_dt and assumption_set are imported from policy_models

arg_extract = create_argument(
    name="extract",
    description="""The active life extract to use. See idi_model/schema/active_life_schema.yaml for specification.""",
    dtype=pd.DataFrame,
)

arg_policy_model = create_argument(
    name="policy_model",
    description="The policy model to deploy either determinstic or stochastic",
    dtype=str,
    allowed=["deterministic", "stochastic"],
)


#########################################################################################
# functions
#########################################################################################


def find_extract_issues(
    extract: pd.DataFrame,  # , valuation_dt: pd.Timestamp, schema: pd.DataFrame
):
    """Find extract issues"""
    return extract


def _dispatch_model_per_record(
    policy_model, record_keys: list, extract: pd.DataFrame, **kwargs
):
    @delayed
    def run_model(**kwargs):
        try:
            ret = policy_model(**kwargs).run()
        except:
            ex_type, ex_value, ex_trace = sys.exc_info()
            ret = {
                **{key: kwargs.get(key.lower()) for key in record_keys},
                "ERROR_TYPE": ex_type,
                "ERROR_VALUE": ex_value,
                "ERROR_STACKTRACE": format_list(extract_tb(ex_trace)),
            }
        return ret

    extract = extract.copy()
    extract.columns = [col.lower() for col in extract.columns]
    params = set(getfullargspec(policy_model).kwonlyargs)
    extract_params = params.intersection(set(extract.columns))
    records = extract[extract_params].to_dict(orient="records")
    output = [run_model(**record, **kwargs) for record in records]
    successes, errors = [], []
    for result in compute(output)[0]:
        (successes if isinstance(result, pd.DataFrame) else errors).append(result)
    return (successes, errors)


def run_policy_model_per_record(
    extract, valuation_dt, assumption_set, net_benefit_method, policy_model
):
    if policy_model == "deterministic":
        return _dispatch_model_per_record(
            policy_model=alr_deterministic_model,
            record_keys=["POLICY_ID"],
            extract=extract,
            valuation_dt=valuation_dt,
            assumption_set=assumption_set,
            net_benefit_method=net_benefit_method,
        )
    elif policy_model == "stochastic":
        raise NotImplementedError("Stochastic capabilities not implemented yet.")


def create_output(results):
    """Create output"""
    successes = results[0]
    errors = results[1]
    time_0 = pd.concat([success.head(1) for success in successes]).reset_index(drop=True)
    projected = pd.concat(successes)
    return time_0[["POLICY_ID", "ALR"]], projected, errors


#########################################################################################
# steps
#########################################################################################

steps = [
    {
        "name": "find-extract-issues",
        "function": find_extract_issues,
        "args": {
            "extract": arg_extract,
            # "valuation_dt": arg_valuation_dt,
            # "schema": "123",
        },
    },
    {
        "name": "run-policy-model-per-record",
        "function": run_policy_model_per_record,
        "args": {
            "extract": use("find-extract-issues"),
            "valuation_dt": arg_valuation_dt,
            "assumption_set": arg_assumption_set,
            "net_benefit_method": arg_net_benefit_method,
            "policy_model": arg_policy_model,
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

DESCRIPTION = "Model IDI active lives."
active_lives_model = create_model(
    name="ActiveLivesModel", description=DESCRIPTION, steps=steps
)
