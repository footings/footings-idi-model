import os

import pandas as pd
import pytest
from footings.audit import AuditConfig, AuditStepConfig
from footings.testing import assert_footings_files_equal

from footings_idi_model.models import AValRopRPMD

CASES = [
    (
        "test_1",
        {
            "assumption_set": "STAT",
            "valuation_dt": pd.Timestamp("2005-02-10"),
            "policy_id": "M1",
            "gender": "M",
            "tobacco_usage": "N",
            "birth_dt": pd.Timestamp("1970-02-10"),
            "policy_start_dt": pd.Timestamp("2005-02-10"),
            "policy_end_dt": pd.Timestamp("2037-02-10"),
            "elimination_period": 90,
            "idi_market": "INDV",
            "idi_contract": "AS",
            "idi_benefit_period": "TO67",
            "idi_occupation_class": "M",
            "cola_percent": 0.0,
            "withdraw_table": "01CSO",
            "premium_pay_to_dt": pd.Timestamp("2005-02-10"),
            "gross_premium": 10.0,
            "gross_premium_freq": "MONTH",
            "benefit_amount": 10.0,
            "net_benefit_method": "PT2",
            "rop_return_freq": 10,
            "rop_return_percent": 0.5,
            "rop_claims_paid": 0,
        },
    ),
]


@pytest.fixture(scope="session")
def tempdir(tmpdir_factory):
    dir_name = os.path.dirname(__file__).split("/")[-1]
    return tmpdir_factory.mktemp(dir_name)


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_active_deterministic_rop(case, tempdir):
    name, parameters = case
    test_file = tempdir.join(f"test-{name}.json")
    expected_file = os.path.join(
        os.path.dirname(__file__), "audit_files", f"expected-{name}.json",
    )
    config = AuditConfig(
        show_signature=False,
        show_docstring=False,
        show_steps=True,
        step_config=AuditStepConfig(
            show_method_name=False,
            show_docstring=False,
            show_uses=True,
            show_impacts=True,
            show_output=True,
            show_metadata=False,
        ),
    )
    AValRopRPMD(**parameters).audit(test_file, config=config)
    exlcude_list = ["*RUN_DATE_TIME", "*MODEL_VERSION", "*LAST_COMMIT"]
    assert_footings_files_equal(test_file, expected_file, exclude_keys=exlcude_list)
