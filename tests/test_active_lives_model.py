import pandas as pd

from footings_idi_model.population_models import active_lives_model


def test_active_lives_model():
    base_extract = pd.read_csv(
        "./tests/data/active-lives-sample-base.csv",
        parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"],
    )
    rider_extract = pd.read_csv(
        "./tests/data/active-lives-sample-riders.csv",
    )
    time0, projected, errors = active_lives_model(
        base_extract=base_extract,
        rider_extract=rider_extract,
        valuation_dt=pd.Timestamp("2020-03-31"),
        assumption_set="stat",
        net_benefit_method="NLP",
        model_type="deterministic",
    ).run()

    assert isinstance(time0, pd.DataFrame)
    assert isinstance(projected, pd.DataFrame)
    assert isinstance(errors, list)
