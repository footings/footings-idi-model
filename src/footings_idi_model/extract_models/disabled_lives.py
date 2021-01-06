import pandas as pd
from dask import compute
from dask.delayed import delayed

from footings import (
    def_return,
    def_parameter,
    def_intermediate,
    step,
    model,
)
from footings.model_tools import make_foreach_model, convert_to_records

from ..attributes import (
    param_assumption_set,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
    modifier_ctr,
    modifier_interest,
)
from ..policy_models.disabled_deterministic_base import (
    DValBasePMD,
    OUTPUT_COLS as DETERMINSTIC_COLS,
)
from ..schemas import disabled_life_columns


foreach_model = make_foreach_model(
    DValBasePMD,
    iterator_name="records",
    iterator_params=[col.lower() for col in disabled_life_columns],
    iterator_key=("policy_id", "claim_id", "coverage_id",),
    success_wrap=pd.concat,
    delay=delayed,
    compute=compute,
)


@model(steps=["_create_records", "_run_foreach", "_get_time0"])
class DisabledLivesValEMD:
    """Disabled lives deterministic valuation extract model.

    This model takes an extract of policies and runs them through the respective Policy Models
    based on the COVERAGE_ID column (i.e., whether it is base policy or rider).
    """

    # parameters
    extract = def_parameter(dtype=pd.DataFrame, description="The disabled lives extract.")
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set

    # sensitivities
    ctr_modifier = modifier_ctr
    interest_modifier = modifier_interest

    # meta
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    # intermediates
    records = def_intermediate(
        dtype=dict, description="The extract transformed to records."
    )

    # return
    projected = def_return(
        dtype=pd.DataFrame, description="The projected reserves for the policyholders."
    )
    time_0 = def_return(
        dtype=pd.DataFrame, description="The time 0 reserve for the policyholders."
    )
    errors = def_return(dtype=list, description="Any errors captured.")

    @step(name="Create Records from Extract", uses=["extract"], impacts=["records"])
    def _create_records(self):
        """Turn extract into a list of records for each row in extract."""
        self.records = convert_to_records(self.extract, column_case="lower")

    @step(
        name="Run Records with Policy Models",
        uses=["records", "valuation_dt", "assumption_set"],
        impacts=["projected", "errors"],
    )
    def _run_foreach(self):
        """Foreach record run through respective policy model based on COVERAGE_ID value."""
        projected, errors = foreach_model(
            records=self.records,
            valuation_dt=self.valuation_dt,
            assumption_set=self.assumption_set,
            interest_modifier=self.interest_modifier,
            ctr_modifier=self.ctr_modifier,
        )
        if isinstance(projected, list):
            projected = pd.DataFrame(columns=DETERMINSTIC_COLS)
        self.projected = projected
        self.errors = errors

    @step(name="Get Time0 Values", uses=["projected"], impacts=["time_0"])
    def _get_time0(self):
        """Filter projected reserves frame down to time_0 reserve for each record."""
        cols = [
            "MODEL_VERSION",
            "LAST_COMMIT",
            "RUN_DATE_TIME",
            "SOURCE",
            "POLICY_ID",
            "CLAIM_ID",
            "COVERAGE_ID",
            "DATE_DLR",
            "DLR",
        ]
        self.time_0 = self.projected.groupby(cols[4:7], as_index=False).head(1)[cols]


@model
class DisabledLivesProjEMD:
    extract = def_parameter(dtype=pd.DataFrame, description="The disabled lives extract.")
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    ctr_modifier = modifier_ctr
    interest_modifier = modifier_interest
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time
