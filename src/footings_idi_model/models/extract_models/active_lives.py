import pandas as pd
from footings.actuarial_tools import convert_to_records
from footings.model import def_intermediate, def_parameter, def_return, model, step
from footings.parallel_tools.dask import create_dask_foreach_jig

from ...outputs import ActiveLivesValOutput
from ..policy_models import (
    AValBasePMD,
    AValCatRPMD,
    AValColaRPMD,
    AValResRPMD,
    AValRopRPMD,
    AValSisRPMD,
)
from ..shared import (
    meta_last_commit,
    meta_model_version,
    meta_run_date_time,
    modifier_incidence,
    modifier_interest,
    param_assumption_set,
    param_net_benefit_method,
    param_valuation_dt,
)

models = {
    "BASE": AValBasePMD,
    "CAT": AValCatRPMD,
    "COLA": AValColaRPMD,
    "RES": AValResRPMD,
    "ROP": AValRopRPMD,
    "SIS": AValSisRPMD,
}

foreach_model = create_dask_foreach_jig(
    models,
    iterator_name="records",
    iterator_keys=("policy_id", "coverage_id",),
    mapped_keys=("coverage_id",),
    pass_iterator_keys=("policy_id",),
    constant_params=(
        "valuation_dt",
        "assumption_set",
        "net_benefit_method",
        "interest_modifier",
        "incidence_modifier",
        "withdraw_modifier",
    ),
    success_wrap=pd.concat,
)


@model(steps=["_create_records", "_run_foreach", "_get_time0"])
class ActiveLivesValEMD:
    """Active lives deterministic valuation extract model.

    This model takes an extract of policies and runs them through the respective Policy Models
    based on the COVERAGE_ID column (i.e., whether it is base policy or rider).
    """

    # parameters
    base_extract = def_parameter(
        dtype=pd.DataFrame, description="The base active lives extract."
    )
    rider_rop_extract = def_parameter(
        dtype=pd.DataFrame, description="The ROP rider active lives extract."
    )
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method

    # sensitivities
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence

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
        dtype=pd.DataFrame, description="The time 0 reserve for the policyholders"
    )
    errors = def_return(dtype=list, description="Any errors captured.")

    @step(name="Create Records from Extract", uses=["base_extract"], impacts=["records"])
    def _create_records(self):
        """Turn extract into a list of records for each row in extract."""
        records = convert_to_records(self.base_extract, column_case="lower")
        idx_cols = ["policy_id", "coverage_id"]

        rider_records = (
            self.rider_rop_extract.rename(columns=str.lower)
            .set_index(idx_cols)
            .to_dict(orient="index")
        )

        def update_record(record):
            key = (
                record["policy_id"],
                record["coverage_id"],
            )
            kwargs_add = rider_records.get(key, None)
            if kwargs_add is not None:
                return {**record, **kwargs_add}
            return record

        self.records = [
            record if record["coverage_id"] not in ["ROP"] else update_record(record)
            for record in records
        ]

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
            net_benefit_method=self.net_benefit_method,
            interest_modifier=self.interest_modifier,
            incidence_modifier=self.incidence_modifier,
            withdraw_modifier=self.withdraw_modifier,
        )
        if isinstance(projected, list):
            projected = pd.DataFrame(columns=list(ActiveLivesValOutput.columns))
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
            "COVERAGE_ID",
            "ALR_DATE",
            "ALR",
        ]
        self.time_0 = self.projected.groupby(cols[4:6], as_index=False).head(1)[cols]


@model
class ActiveLivesProjEMD:
    # parameters
    base_extract = def_parameter(
        dtype=pd.DataFrame, description="The base active lives extract."
    )
    rider_extract = def_parameter(
        dtype=pd.DataFrame, description="The rider active lives extract."
    )
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method

    # sensitivities
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence

    # meta
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time
