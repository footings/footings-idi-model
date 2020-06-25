import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec

from dask import compute
from dask.delayed import delayed
import pandas as pd

from footings import create_dispatch_function


def find_extract_issues(
    extract: pd.DataFrame,  # , valuation_dt: pd.Timestamp, schema: pd.DataFrame
):
    """Find extract issues"""
    return extract


dispatch_model_per_record = create_dispatch_function(
    "dispatch_model_per_record", parameters=("backend",)
)


@dispatch_model_per_record.register(backend="dask")
def _(policy_model, record_keys: list, extract: pd.DataFrame, **kwargs):
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


@dispatch_model_per_record.register(backend="ray")
def _(policy_model, record_keys: list, extract: pd.DataFrame, **kwargs):
    @ray.remote
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
    output = [run_model.remote(**record, **kwargs) for record in records]
    successes, errors = [], []
    for result in ray.get(output):
        (successes if isinstance(result, pd.DataFrame) else errors).append(result)
    return (successes, errors)


@dispatch_model_per_record.register(backend="base")
def _(policy_model, record_keys: list, extract: pd.DataFrame, **kwargs):
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
    for result in output:
        (successes if isinstance(result, pd.DataFrame) else errors).append(result)
    return (successes, errors)
