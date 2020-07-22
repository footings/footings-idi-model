from footings_idi_model.utils import extract_generator_model
from footings.tools import calculate_age
import pandas as pd

volume_tbl = pd.read_csv("tests/data/volume-tbl.csv")

disabled_extract = extract_generator_model(
    n=10000,
    extract_type="disabled-lives",
    volume_tbl=volume_tbl,
    seed=1,
    as_of_dt=pd.Timestamp("2020-06-30"),
).run()

active_extract = extract_generator_model(
    n=10000,
    extract_type="active-lives",
    volume_tbl=volume_tbl,
    seed=1,
    as_of_dt=pd.Timestamp("2020-06-30"),
).run()

grp_cols = [
    "IDI_OCCUPATION_CLASS",
    "IDI_CONTRACT",
    "IDI_BENEFIT_PERIOD",
    "IDI_MARKET",
    "GENDER",
    "TOBACCO_USAGE",
]
disabled_sample = (
    disabled_extract.groupby(grp_cols)
    .first()
    .assign(
        AGE_AT_DISABLEDMENT=lambda df: calculate_age(
            df["BIRTH_DT"], df["INCURRED_DT"], "ALB"
        )
    )
    .reset_index()
)

disabled_sample.to_csv("tests/data/disabled-lives-sample.csv", index=False)

active_sample = (
    active_extract.groupby(grp_cols)
    .first()
    .assign(
        ISSUE_AGE=lambda df: calculate_age(
            df["BIRTH_DT"], pd.Timestamp("2020-06-30"), "ALB"
        ),
        SELECT_COLA=lambda df: [
            "N" if x == 0 else "Y" for x in df["COLA_PERCENT"].tolist()
        ],
        PREMIUM_PAY_TO_AGE=lambda df: calculate_age(
            df["BIRTH_DT"], df["TERMINATION_DT"], "ALB"
        ),
        COVERAGE_TO_AGE=lambda df: df["PREMIUM_PAY_TO_AGE"],
    )
    .reset_index()
)

active_sample.to_csv("tests/data/active-lives-sample.csv", index=False)
