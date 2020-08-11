import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec

from dask import compute
from dask.delayed import delayed
import pandas as pd

from footings import dispatch_function

from ..policy_models import (
    dlr_deterministic_model,
    alr_deterministic_model,
    rop_deterministic_model,
)


@delayed
def _run_model(model, record_keys, **kwargs):
    try:
        params = set(getfullargspec(model).kwonlyargs)
        ret = model(**{k: v for k, v in kwargs.items() if k in params}).run()
    except:
        ex_type, ex_value, ex_trace = sys.exc_info()
        ret = {
            **{key: kwargs.get(key.lower()) for key in record_keys},
            "ERROR_TYPE": ex_type,
            "ERROR_VALUE": ex_value,
            "ERROR_STACKTRACE": format_list(extract_tb(ex_trace)),
        }
    return ret


@dispatch_function(key_parameters=("coverage_id", "policy_type", "model_type",))
def run_model(coverage_id, policy_type, model_type, **kwargs):
    raise NotImplementedError()


@run_model.register(coverage_id="base", policy_type="active", model_type="deterministic")
def _(**kwargs):
    return _run_model(model=alr_deterministic_model, record_keys=["POLICY_ID"], **kwargs)


@run_model.register(coverage_id="rop", policy_type="active", model_type="deterministic")
def _(**kwargs):
    return _run_model(model=rop_deterministic_model, record_keys=["POLICY_ID"], **kwargs)


@run_model.register(
    coverage_id="base", policy_type="disabled", model_type="deterministic"
)
def _(**kwargs):
    return _run_model(
        model=dlr_deterministic_model, record_keys=["POLICY_ID", "CLAIM_ID"], **kwargs
    )


def dispatch_model_per_record(records: list, policy_type: str, model_type: str, **kwargs):

    output = [
        run_model(policy_type=policy_type, model_type=model_type, **record, **kwargs)
        for record in records
    ]
    successes, errors = [], []
    for result in compute(output)[0]:
        (successes if isinstance(result, pd.DataFrame) else errors).append(result)
    return (successes, errors)
