import os

import pytest
import pandas as pd

from footings.audit import AuditConfig, AuditStepConfig
from footings_idi_model.policy_models import ROPDeterministicPolicyModel
from footings.test_tools import assert_footings_files_equal

CASES = [
    (
        "test_1",
        {
            "assumption_set": "stat",
            "valuation_dt": pd.Timestamp("2005-02-10"),
            "policy_id": "M1",
            "coverage_id": "rop",
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
            "gross_premium": 150.0,
            "benefit_amount": 100.0,
            "net_benefit_method": "PT2",
            "rop_return_frequency": 10,
            "rop_return_percentage": 0.5,
            "rop_claims_paid": 0,
            "rop_future_claims_start_dt": pd.Timestamp("2005-02-10"),
        },
    ),
]


@pytest.fixture(scope="session")
def tempdir(tmpdir_factory):
    return tmpdir_factory.mktemp("rop_deterministic")


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_rop_deterministic(case, tempdir):
    name, parameters = case
    test_file = tempdir.join(f"test-{name}.json")
    expected_file = os.path.join(
        "tests",
        "policy_models",
        "rop_deterministic",
        "audit_files",
        f"expected-{name}.json",
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
    ROPDeterministicPolicyModel(**parameters).audit(test_file, config=config)
    exlcude_list = ["*/RUN_DATE_TIME/", "*/MODEL_VERSION/", "*/LAST_COMMIT/"]
    assert_footings_files_equal(test_file, expected_file, exclude_keys=exlcude_list)
