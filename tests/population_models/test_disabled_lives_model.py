import os

import pytest
import pandas as pd

from footings_idi_model.population_models import DisabledLivesDeterministicModel
from footings.test_tools import assert_footings_files_equal

extract_file = os.path.join("tests", "population_models", "disabled-lives-sample.csv")
extract = pd.read_csv(
    extract_file, parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"]
)

CASES = [
    (
        "test_1",
        {
            "extract": extract[:5],
            "valuation_dt": pd.Timestamp("2020-03-31"),
            "assumption_set": "stat",
        },
    ),
]


@pytest.fixture(scope="session")
def tempdir(tmpdir_factory):
    return tmpdir_factory.mktemp("disabled-lives")


@pytest.mark.parametrize("case", CASES, ids=[x[0] for x in CASES])
def test_disabled_lives_deterministic_model(case, tempdir):
    name, parameters = case
    test_file = tempdir.join(f"test-{name}.xlsx")
    expected_file = os.path.join(
        "tests",
        "population_models",
        "disabled_lives_audit_files",
        f"expected-{name}.xlsx",
    )
    DisabledLivesDeterministicModel(**parameters).audit(test_file)
    exlcude_list = [
        {"worksheet": "_run_foreach", "column_name": "RUN_DATE_TIME",},
        {"worksheet": "_run_foreach", "column_name": "MODEL_VERSION",},
        {"worksheet": "_run_foreach", "column_name": "LAST_COMMIT",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "RUN_DATE_TIME",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "MODEL_VERSION",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "LAST_COMMIT",},
    ]
    assert_footings_files_equal(test_file, expected_file, exclude=exlcude_list)
