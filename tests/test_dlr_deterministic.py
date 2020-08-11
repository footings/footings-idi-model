import pandas as pd

from footings_idi_model.policy_models import dlr_deterministic_model


def test_dlr_deterministic():
    kwargs = {
        "valuation_dt": pd.Timestamp("2005-02-10"),
        "policy_id": "M1",
        "claim_id": "M1C1",
        "gender": "M",
        "birth_dt": pd.Timestamp("1970-02-10"),
        "incurred_dt": pd.Timestamp("2005-02-10"),
        "termination_dt": pd.Timestamp("2037-02-10"),
        "elimination_period": 90,
        "idi_diagnosis_grp": "AG",
        "idi_contract": "AS",
        "idi_benefit_period": "TO67",
        "idi_occupation_class": "M",
        "cola_percent": 0.0,
        "assumption_set": "stat",
        "benefit_amount": 100.0,
    }

    df = dlr_deterministic_model(**kwargs).run()
    df.to_csv("frame-dlr.csv", index=False)
    assert isinstance(df, pd.DataFrame)
