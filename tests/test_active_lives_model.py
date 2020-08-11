import pandas as pd

from footings_idi_model.population_models import active_lives_model


def add_rop_policies_to_extract(extract):
    extract_rop = extract.copy()
    extract_rop["COVERAGE_ID"] = "rop"
    return pd.concat([extract, extract_rop], axis=0).sort_values(by=["POLICY_ID"], ignore_index=True)


def test_active_lives_model():
    extract = pd.read_csv(
        "./tests/data/active-lives-sample.csv",
        parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"],
    )
    time0, projected, errors = active_lives_model(
        extract=extract,
        valuation_dt=pd.Timestamp("2020-03-31"),
        assumption_set="stat",
        net_benefit_method="NLP",
        model_type="deterministic",
    ).run()

    assert isinstance(time0, pd.DataFrame)
    assert isinstance(projected, pd.DataFrame)
    assert isinstance(errors, list)
