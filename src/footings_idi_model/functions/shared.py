import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec

from dask import compute
from dask.delayed import delayed
import pandas as pd


def dispatch_model_per_record(
    policy_model: callable, record_keys: list, extract: pd.DataFrame, **kwargs
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
