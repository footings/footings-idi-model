import sys
from traceback import extract_tb, format_list
from inspect import getfullargspec
from typing import Tuple

import pandas as pd
from dask import compute
from dask.delayed import delayed

from footings import (
    define_asset,
    define_meta,
    define_modifier,
    define_parameter,
    Footing,
    step,
    model,
)

from ..parameters import (
    param_assumption_set,
    param_active_base_extract,
    param_active_rider_extract,
    param_model_type,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
)
from ..policy_models.alr_deterministic import OUTPUT_COLS
from ..__init__ import __version__ as MOD_VERSION
from ..__init__ import __git_revision__ as GIT_REVISION
from .dispatch_model import dispatch_model_per_record


STEPS = [
    "_check_extract",
    "_run_policy_model_per_record",
]


@model(steps=STEPS)
class ActiveLivesModel(Footings):
    """Model to calculate active life reserves (ALRs) using the 2013 individual
    disability insurance (IDI) valuation standard.

    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

    The key assumptions underlying the model are -

    * `Incidence Rates` - The probablility of an individual becoming disabled.
    * `Termination Rates` - Given an an individual is disabled, the probability of an individual going off claim.

    """

    base_extract = param_active_base_extract
    rider_extract = param_active_rider_extract
    assumption_set = param_assumption_set
    model_type = param_model_type
    valuation_dt = param_valuation_dt
    time_0_output = define_asset(dtype=pd.DataFrame)
    projected_output = define_asset(dtype=pd.DataFrame)
    errors = define_asset(dtype=pd.DataFrame)
    lapse_modifier = define_modifier(default=1.0)
    interest_modifier = define_modifier(default=1.0)
    incidence_modifier = define_modifier(default=1.0)
    model_version = define_meta(meta=MOD_VERSION)
    last_commit = define_meta(meta=GIT_REVISION)
    run_date_time = define_meta(meta=pd.to_datetime("now"))

    @step(uses=["extract"], impacts=[])
    def check_extracts(self):
        """Check extract against required schema.

        Returns
        -------
        pd.DataFrame
            The extract.
        """
        pass

    @step(
        uses=[
            "base_extract",
            "rider_extract",
            "assumption_set",
            "model_type",
            "net_benefit_method",
        ],
        impacts=["time_0_output", "projected_output", "errors"],
    )
    def run_policy_model_per_record(self):
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

        base_extract = self.base_extract.copy()
        base_extract.columns = [col.lower() for col in base_extract.columns]

        rider_extract = self.rider_extract.copy()
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

        successes, errors = dispatch_model_per_record(
            records=records,
            policy_type="active",
            model_type=self.model_type,
            valuation_dt=self.valuation_dt,
            assumption_set=self.assumption_set,
            net_benefit_method=self.net_benefit_method,
        )

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

        self.time_0_output = time_0[time_0_cols]
        self.projected = projected
        self.errors = errors
