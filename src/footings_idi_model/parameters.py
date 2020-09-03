import pandas as pd
from footings_idi_model import define_parameter

param_n_simulations = define_parameter(
    name="n_simulations",
    description="The number of simulations to run.",
    default=1000,
    dtype=int,
)

param_seed = define_parameter(
    name="seed",
    description="The seed passed to numpy.random.seed.",
    default=42,
    dtype=int,
)

param_valuation_dt = define_parameter(
    name="valuation_dt",
    description="The valuation date which reserves are based.",
    dtype=pd.Timestamp,
)

param_assumption_set = define_parameter(
    name="assumption_set",
    description="""The assumption set to use for running the model. Options are :
    
        * `stat`
        * `gaap`
        * `best-estimate`
    """,
    dtype=str,
    allowed=["stat", "gaap", "best-estimate"],
)

param_disabled_extract = define_parameter(
    name="extract",
    description="The disabled life extract to use. See idi_model/schema/disabled_life_schema.yaml for specification.",
    dtype=pd.DataFrame,
)

param_active_base_extract = define_parameter(
    name="base_extract",
    description="""The active life base extract to use. See idi_model/schema/extract-active-lives-base.yaml for specification.""",
    dtype=pd.DataFrame,
)

param_active_rider_extract = define_parameter(
    name="rider_extract",
    description="""The active life rider extract to use. See idi_model/schema/extract-active-lives-riders.yaml for specification.""",
    dtype=pd.DataFrame,
)

param_model_type = define_parameter(
    name="model_type",
    description="""The policy model to deploy. Options are :

        * `determinstic`
        * `stochastic`
    """,
    dtype=str,
    allowed=["deterministic", "stochastic"],
)

param_net_benefit_method = define_parameter(
    name="net_benefit_method",
    description="""The net benefit method. Options are :

        * `NLP` = Net level premium
        * `PT1` = 1 year preliminary term
        * `PT2` = 2 year preliminary term
    """,
    dtype=str,
    allowed=["NLP", "PT1", "PT2"],
)
