import pandas as pd

from idi_model.policy_models.alr_deterministic import alr_deterministic_model


def test_create_alr_frame():
    kwargs = {
        "valuation_dt": pd.Timestamp("2005-02-10"),
        "policy_id": "M1",
        "gender": "M",
        "tobacco_usage": "N",
        "birth_dt": pd.Timestamp("1970-02-10"),
        "issue_dt": pd.Timestamp("2005-02-10"),
        "termination_dt": pd.Timestamp("2037-02-10"),
        "elimination_period": 90,
        "idi_market": "INDV",
        "idi_contract": "AS",
        "idi_benefit_period": "TO67",
        "idi_occupation_class": "M",
        "cola_percent": 0.0,
        "assumption_set": "stat",
        "benefit_amount": 100.0,
        "net_benefit_method": "PT2",
    }

    df = alr_deterministic_model(**kwargs).run()
    # df.to_csv("frame-alr.csv", index=False)
    assert isinstance(df, pd.DataFrame)
