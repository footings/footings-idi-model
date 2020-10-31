import pandas as pd

from footings_idi_model.policy_models.alr_deterministic import (
    alr_deterministic_model,
    rop_deterministic_model,
)


def test_alr_deterministic_model():
    ret = alr_deterministic_model(
        valuation_dt=pd.Timestamp("2005-02-10"),
        policy_id="M1",
        coverage_id="base",
        gender="M",
        tobacco_usage="N",
        birth_dt=pd.Timestamp("1970-02-10"),
        policy_start_dt=pd.Timestamp("2005-02-10"),
        policy_end_dt=pd.Timestamp("2037-02-10"),
        elimination_period=90,
        idi_market="INDV",
        idi_contract="AS",
        idi_benefit_period="TO67",
        idi_occupation_class="M",
        cola_percent=0.0,
        assumption_set="stat",
        benefit_end_id="",
        gross_premium=150.0,
        benefit_amount=100.0,
        net_benefit_method="PT2",
    ).run()
    assert isinstance(ret, pd.DataFrame)


def test_rop_deterministic_model():
    ret = rop_deterministic_model(
        valuation_dt=pd.Timestamp("2005-02-10"),
        policy_id="M1",
        gender="M",
        coverage_id="rop",
        tobacco_usage="N",
        birth_dt=pd.Timestamp("1970-02-10"),
        policy_start_dt=pd.Timestamp("2005-02-10"),
        policy_end_dt=pd.Timestamp("2037-02-10"),
        elimination_period=90,
        idi_market="INDV",
        idi_contract="AS",
        idi_benefit_period="TO67",
        idi_occupation_class="M",
        cola_percent=0.0,
        assumption_set="stat",
        benefit_end_id="",
        gross_premium=150.0,
        benefit_amount=100.0,
        net_benefit_method="NLP",
        rop_return_frequency=5,
        rop_return_percentage=0.8,
        rop_claims_paid=0.0,
        rop_future_claims_start_dt=pd.Timestamp("2005-02-10"),
    ).run()
    assert isinstance(ret, pd.DataFrame)
