import pandas as pd

from footings_idi_model.population_models import disabled_lives_model


def test_disabled_lives_deterministic_model():
    extract = pd.read_csv(
        "./tests/data/disabled-lives-sample.csv",
        parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"],
    )
    time0, projected, errors = disabled_lives_model(
        extract=extract[:5],
        valuation_dt=pd.Timestamp("2020-03-31"),
        assumption_set="stat",
        model_type="deterministic",
    ).run()

    assert isinstance(time0, pd.DataFrame)
    assert isinstance(projected, pd.DataFrame)
    assert isinstance(errors, list)


def test_disabled_lives_stochastic_model():
    extract = pd.read_csv(
        "./tests/data/disabled-lives-sample.csv",
        parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"],
    )
    time0, projected, errors = disabled_lives_model(
        extract=extract[:5],
        valuation_dt=pd.Timestamp("2020-03-31"),
        assumption_set="stat",
        model_type="stochastic",
        n_simulations=10,
        seed=1,
    ).run()

    assert isinstance(time0, pd.DataFrame)
    assert isinstance(projected, pd.DataFrame)
    assert isinstance(errors, list)
