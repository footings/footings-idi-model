import os

import pytest
import pandas as pd

from footings.audit import AuditConfig, AuditStepConfig
from footings_idi_model.policy_models import DValBasePM
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
    dir_name = os.path.dirname(__file__).split("/")[-1]
    return tmpdir_factory.mktemp(dir_name)


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_disabled_deterministic_base(case, tempdir):
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
    DValBasePM(**parameters).audit(test_file, config=config)
    exlcude_list = exlcude_list = [
        "*RUN_DATE_TIME",
        "*MODEL_VERSION",
        "*LAST_COMMIT",
    ]
    assert_footings_files_equal(
        test_file, expected_file, tolerance=0.01, exclude_keys=exlcude_list
    )
