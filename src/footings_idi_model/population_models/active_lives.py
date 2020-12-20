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
    param_net_benefit_method,
    param_withdraw_table,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
    modifier_interest,
    modifier_incidence,
    modifier_withdraw,
)
from ..policy_models.alr_deterministic import (
    ALRDeterministicPolicyModel,
    OUTPUT_COLS as DETERMINSTIC_COLS,
)
from ..schemas import active_lives_base_columns


foreach_model = make_foreach_model(
    ALRDeterministicPolicyModel,
    iterator_name="records",
    iterator_params=[col.lower() for col in active_lives_base_columns],
    iterator_key=("policy_id",),
    success_wrap=pd.concat,
    delay=delayed,
    compute=compute,
)


@model(steps=["_create_records", "_run_foreach", "_get_valuation_dt_values"])
class ActiveLivesDeterministicModel:
    base_extract = def_parameter(
        dtype=pd.DataFrame, description="The base active lives extract."
    )
    rider_extract = def_parameter(
        dtype=pd.DataFrame, description="The rider active lives extract."
    )
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    net_benefit_method = param_net_benefit_method
    withdraw_table = param_withdraw_table
    interest_modifier = modifier_interest
    incidence_modifier = modifier_incidence
    withdraw_modifier = modifier_withdraw
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time
    records = def_intermediate(
        dtype=dict, description="The extract transformed to records."
    )
    projected = def_return(
        dtype=pd.DataFrame, description="The projected reserves for the policyholders."
    )
    time_0 = def_return(
        dtype=pd.DataFrame, description="The time 0 reserve for the policyholders"
    )
    errors = def_return(dtype=list, description="Any errors captured.")

    @step(uses=["base_extract"], impacts=["records"])
    def _create_records(self):
        """Create records from extract."""
        self.records = convert_to_records(self.base_extract, column_case="lower")

    @step(
        uses=["records", "valuation_dt", "assumption_set", "withdraw_table"],
        impacts=["projected", "errors"],
    )
    def _run_foreach(self):
        """Run the policy model foreach record."""
        projected, errors = foreach_model(
            records=self.records,
            valuation_dt=self.valuation_dt,
            withdraw_table=self.withdraw_table,
            assumption_set=self.assumption_set,
            net_benefit_method=self.net_benefit_method,
            interest_modifier=self.interest_modifier,
            incidence_modifier=self.incidence_modifier,
            withdraw_modifier=self.withdraw_modifier,
        )
        if isinstance(projected, list):
            projected = pd.DataFrame(columns=DETERMINSTIC_COLS)
        self.projected = projected
        self.errors = errors

    @step(uses=["projected"], impacts=["time_0"])
    def _get_valuation_dt_values(self):
        """Get valuation date reserve values."""
        self.time_0 = self.projected.groupby(
            ["POLICY_ID", "COVERAGE_ID"], as_index=False
        ).head(1)
