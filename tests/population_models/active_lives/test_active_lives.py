import os

import pytest
import pandas as pd

from footings.audit import AuditConfig, AuditStepConfig
from footings_idi_model.population_models import ActiveLivesDeterministicModel
from footings.test_tools import assert_footings_files_equal

extract_base_file = os.path.join(
    "tests", "population_models", "active_lives", "extract-base.csv"
)
base_extract = pd.read_csv(
    extract_base_file,
    parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"],
)

extract_rider_file = os.path.join(
    "tests", "population_models", "active_lives", "extract-riders.csv"
)
rider_extract = pd.read_csv(extract_rider_file)


CASES = [
    (
        "test_1",
        {
            "base_extract": base_extract,
            "rider_extract": rider_extract,
            "valuation_dt": pd.Timestamp("2020-03-31"),
            "withdraw_table": "01CSO",
            "assumption_set": "stat",
            "net_benefit_method": "NLP",
        },
    ),
]


@pytest.fixture(scope="session")
def tempdir(tmpdir_factory):
    return tmpdir_factory.mktemp("active-lives")


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_active_lives_model(case, tempdir):
    name, parameters = case
    test_file = tempdir.join(f"test-{name}.json")
    expected_file = os.path.join(
        "tests",
        "population_models",
        "active_lives",
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
    ActiveLivesDeterministicModel(**parameters).audit(test_file, config=config)
    exlcude_list = exlcude_list = [
        "*RUN_DATE_TIME",
        "*MODEL_VERSION",
        "*LAST_COMMIT",
    ]
    assert_footings_files_equal(test_file, expected_file, exclude_keys=exlcude_list)
