import os

import pytest
import pandas as pd

from footings_idi_model.policy_models import DLRDeterministicPolicyModel
from footings.test_tools import assert_footings_files_equal

CASES = [
    (
        "test_1",
        {
            "valuation_dt": pd.Timestamp("2005-02-10"),
            "assumption_set": "stat",
            "policy_id": "M1",
            "claim_id": "M1C1",
            "gender": "M",
            "birth_dt": pd.Timestamp("1970-02-10"),
            "incurred_dt": pd.Timestamp("2005-02-10"),
            "termination_dt": pd.Timestamp("2037-02-10"),
            "elimination_period": 90,
            "idi_contract": "AS",
            "idi_benefit_period": "TO67",
            "idi_diagnosis_grp": "AG",
            "idi_occupation_class": "M",
            "cola_percent": 0.0,
            "benefit_amount": 100.0,
        },
    ),
]


@pytest.fixture(scope="session")
def tempdir(tmpdir_factory):
    return tmpdir_factory.mktemp("dlr_deterministic")


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_dlr_deterministic(case, tempdir):
    name, parameters = case
    test_file = tempdir.join(f"test-{name}.xlsx")
    expected_file = os.path.join(
        "tests", "policy_models", "dlr_deterministic_audit_files", f"expected-{name}.xlsx"
    )
    DLRDeterministicPolicyModel(**parameters).audit(test_file)
    exlcude_list = [
        {"worksheet": "_to_output", "column_name": "RUN_DATE_TIME",},
        {"worksheet": "_to_output", "column_name": "MODEL_VERSION",},
        {"worksheet": "_to_output", "column_name": "LAST_COMMIT",},
    ]
    assert_footings_files_equal(test_file, expected_file, exclude=exlcude_list)
