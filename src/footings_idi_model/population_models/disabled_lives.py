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
    param_extract,
    param_model_type,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
)
from ..policy_models.dlr_deterministic import OUTPUT_COLS as DETERMINSTIC_COLS
from ..policy_models.dlr_stochastic import OUTPUT_COLS as STOCHASTIC_COLS
from ..__init__ import __version__ as MOD_VERSION
from ..__init__ import __git_revision__ as GIT_REVISION
from .dispatch_model import dispatch_model_per_record


STEPS = [
    "_check_extract",
    "_run_policy_model_per_record",
]


@model(steps=STEPS)
class DisabledLivesModel(Footing):
    """A population model to calculate disabled life reserves (DLRs) using the 2013 individual
    disability insurance (IDI) valuation standard.

    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

    The key assumption underlying the model is -

    * `Termination Rates` - the probability of an individual going off claim.

    """

    extract = param_extract
    assumption_set = param_assumption_set
    model_type = param_model_type
    valuation_dt = param_valuation_dt
    n_simulations = param_n_simulations
    seed = param_seed
    ctr_modifier = define_modifier(default=1.0)
    interst_modifier = define_modifier(default=1.0)
    time_0_output = define_asset(dtype=pd.DataFrame)
    projected_output = define_asset(dtype=pd.DataFrame)
    errors = define_asset(dtype=pd.DataFrame)
    model_version = define_meta(meta=MOD_VERSION)
    last_commit = define_meta(meta=GIT_REVISION)
    run_date_time = define_meta(meta=pd.to_datetime("now"))

    @step(uses=["extract"], impacts=[])
    def _check_extract(self):
        """Check extract against required schema.

        Returns
        -------
        pd.DataFrame
            The extract.
        """
        pass

    @step(
        uses=[
            "extract",
            "model_type",
            "assumption_set",
            "n_simulations",
            "seed",
            "valuation_dt",
        ],
        impacts=["time_0_output", "projected_output", "errors"],
    )
    def _run_policy_model_per_record(self):
        """Run each policy in extract through specified policy model.

        Parameters
        ----------
        extract : pd.DataFrame
            The extract to run.
        valuation_dt : pd.Timestamp
            The valuation date to be modeled.
        assumption_set : str
            The assumptions set to model.
        model_type : str
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
        extract = self.extract.copy()
        extract.columns = [col.lower() for col in extract.columns]
        records = extract.to_dict(orient="records")
        successes, errors = dispatch_model_per_record(
            records=records,
            policy_type="disabled",
            model_type=self.model_type,
            valuation_dt=self.valuation_dt,
            assumption_set=self.assumption_set,
            n_simulations=self.n_simulations,
            seed=self.seed,
        )

        if self.model_type == "deterministic":
            time_0_cols = [
                "MODEL_VERSION",
                "LAST_COMMIT",
                "RUN_DATE_TIME",
                "POLICY_ID",
                "DLR",
            ]
            OUTPUT_COLS = DETERMINSTIC_COLS

            def prep_time0(df):
                return df.head(1)

        elif self.model_type == "stochastic":
            time_0_cols = [
                "MODEL_VERSION",
                "LAST_COMMIT",
                "RUN_DATE_TIME",
                "POLICY_ID",
                "RUN",
                "DLR",
            ]
            OUTPUT_COLS = STOCHASTIC_COLS

            def prep_time0(df):
                return df.groupby(["RUN"], as_index=False).head(1)

        else:
            raise ValueError("model_type not recognized.")
        try:
            time_0 = pd.concat(
                [prep_time0(success) for success in successes]
            ).reset_index(drop=True)
        except ValueError:
            time_0 = pd.DataFrame(columns=time_0_cols)
        try:
            projected = pd.concat(successes)
        except ValueError:
            projected = pd.DataFrame(columns=OUTPUT_COLS)

        self.time_0_output = time_0[time_0_cols]
        self.projected_output = projected
        self.errors = errors
