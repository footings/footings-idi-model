import os

import pytest
import pandas as pd

from footings_idi_model.population_models import ActiveLivesDeterministicModel
from footings.test_tools import assert_footings_audit_xlsx_equal

extract_base_file = os.path.join(
    "tests", "population_models", "active-lives-sample-base.csv"
)
base_extract = pd.read_csv(
    extract_base_file,
    parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"],
)

extract_rider_file = os.path.join(
    "tests", "population_models", "active-lives-sample-riders.csv"
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
    test_file = tempdir.join(f"test-{name}.xlsx")
    expected_file = os.path.join(
        "tests", "population_models", "active_lives_audit_files", f"expected-{name}.xlsx"
    )
    ActiveLivesDeterministicModel(**parameters).audit(test_file)
    exlcude_list = [
        {"worksheet": "_run_foreach", "column_name": "RUN_DATE_TIME",},
        {"worksheet": "_run_foreach", "column_name": "MODEL_VERSION",},
        {"worksheet": "_run_foreach", "column_name": "LAST_COMMIT",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "RUN_DATE_TIME",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "MODEL_VERSION",},
        {"worksheet": "_get_valuation_dt_values", "column_name": "LAST_COMMIT",},
    ]
    assert_footings_audit_xlsx_equal(test_file, expected_file, exclude=exlcude_list)
