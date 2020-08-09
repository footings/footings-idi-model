import datetime

import numpy as np
import pandas as pd

from footings import dispatch_function

from ..schemas import disabled_life_columns, active_lives_base_columns

#########################################################################################
# functions
#########################################################################################


@dispatch_function(key_parameters=("extract_type",))
def create_frame(extract_type: str, n: int):
    """Create active or disabled life extract.
    
    Parameters
    ----------
    extract_type : str
    n : int
    
    Returns
    -------
    pd.DataFrame
        If extract type is "disabled-lives" a DataFrame with columns POLICY_ID and CLAIM_ID. \n
        If extract type is "active-lives" a DataFrame with columns POLICY_ID.    
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@create_frame.register(extract_type="disabled-lives")
def _(n: int):
    policy_ids = [f"M{i}" for i in range(1, n + 1)]
    claim_ids = [f"{p}C1" for p in policy_ids]
    frame = pd.DataFrame({"POLICY_ID": policy_ids, "CLAIM_ID": claim_ids})
    frame["COVERAGE_ID"] = "base"
    return frame


@create_frame.register(extract_type="active-lives")
def _(n: int):
    policy_ids = [f"M{i}" for i in range(1, n + 1)]
    frame = pd.DataFrame({"POLICY_ID": policy_ids})
    frame["COVERAGE_ID"] = "base"
    return frame


def sample_from_volume_tbl(frame: pd.DataFrame, volume_tbl: pd.DataFrame, seed: int):
    """Sample from volume table.

    Parameters
    ----------
    frame : pd.DataFrame
    volume_tbl : pd.DataFrame
    seed : int

    Returns
    -------
    pd.DataFrame
        A DataFrame with columns joined from volume_tbl.
    """
    np.random.seed(seed)
    frame = frame.copy()
    volume_tbl = volume_tbl.copy()
    frame["WT"] = np.random.uniform(size=frame.shape[0])
    cols = set(frame.columns)
    frame.reset_index(inplace=True)
    cols_added = set(frame.columns) - cols
    frame.sort_values(["WT"], inplace=True)
    total_wt = sum(volume_tbl["WT"])
    volume_tbl["WT"] = volume_tbl["WT"].cumsum() / total_wt
    frame = pd.merge_asof(frame, volume_tbl, on=["WT"]).drop(["WT"], axis=1)
    frame.sort_values(list(cols_added), inplace=True)
    return frame.drop(list(cols_added), axis=1).reset_index(drop=True)


def add_benefit_end_id(frame: pd.DataFrame):
    """Add benefit end id.

    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        The generated frame with an added column - GROSS_PREMIUM
    """
    return frame.assign(BENEFIT_END_ID=pd.NA)


def add_gross_premium(frame: pd.DataFrame):
    """Add gross premium to generated frame.

    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        The generated frame with an added column - GROSS_PREMIUM
    """
    return frame.assign(BENEFIT_AMOUNT=100.0)


def add_benefit_amount(frame: pd.DataFrame):
    """Add benefit amount to generated frame.
    
    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        The generated frame with an added column - BENEFIT_AMOUNT
    """
    return frame.assign(BENEFIT_AMOUNT=100.0)


@dispatch_function(key_parameters=("extract_type",))
def add_premium_and_benefits(frame: pd.DataFrame):
    """Add premium and benefit amount to generated frame.
    
    Parameters
    ----------
    frame : pd.DataFrame


    Returns
    -------
    pd.DataFrame
        If extract type is "disabled-lives" a DataFrame with column BENEFIT_AMOUNT. \n
        If extract type is "active-lives"  a DataFrame with columns BENEFIT_END_ID, GROSS_PREMIUM, and BENEFIT_AMOUNT.
 
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@add_premium_and_benefits.register(extract_type="disabled-lives")
def _(frame):
    return frame.assign(BENEFIT_AMOUNT=100)


@add_premium_and_benefits.register(extract_type="active-lives")
def _(frame):
    return frame.assign(BENEFIT_END_ID=pd.NA, GROSS_PREMIUM=150, BENEFIT_AMOUNT=100)


def _calculate_age(frame: pd.DataFrame, low: float, high: float):
    return np.random.uniform(low=low, high=high, size=frame.shape[0])


def _calculate_termination_age(frame: pd.DataFrame, base_age: int):
    # calculate termination age
    benefit_period = frame["IDI_BENEFIT_PERIOD"].values.astype(str)
    cond_list_1 = [np.char.endswith(benefit_period, "M")]
    choice_list_1 = [np.char.strip(benefit_period, "M")]
    years_add = np.select(cond_list_1, choice_list_1).astype(int) / 1200

    cond_list_2 = [
        np.char.find(benefit_period, "TO") >= 0,
        np.char.find(benefit_period, "LIFE") >= 0,
    ]
    choice_list_2 = [np.char.strip(benefit_period, "TO"), 120]
    end_year = np.select(cond_list_2, choice_list_2).astype(int) / 100

    cond_list_3 = [years_add > 0, end_year > 0]
    choice_list_3 = [base_age + years_add, end_year]
    return np.select(cond_list_3, choice_list_3)


@dispatch_function(key_parameters=("extract_type",))
def calculate_ages(extract_type: str, frame: pd.DataFrame, seed: int):
    """Calculate ages
    
    Parameters
    ----------
    extract_type : str
    frame : pd.DataFrame
    seed : int

    Returns
    -------
    pd.DataFrame
        If extract type is "disabled-lives" a DataFrame with columns CURRENT_AGE, INCURRED_AGE, and TERMINATION_AGE. \n
        If extract type is "active-lives"  a DataFrame with columns CURRENT_AGE and ISSUE_AGE.
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@calculate_ages.register(extract_type="disabled-lives")
def _(frame: pd.DataFrame, seed: int):
    np.random.seed(seed)

    incurred_age = _calculate_age(frame, 0.25, 0.6)
    termination_age = _calculate_termination_age(frame, incurred_age)
    current_age = _calculate_age(frame, incurred_age, termination_age)

    # assign to frame
    frame["CURRENT_AGE"] = current_age * 100
    frame["INCURRED_AGE"] = incurred_age * 100
    frame["TERMINATION_AGE"] = termination_age * 100
    return frame


@calculate_ages.register(extract_type="active-lives")
def _(frame: pd.DataFrame, seed: int):
    np.random.seed(seed)
    issue_age = _calculate_age(frame, 0.25, 0.6)
    frame["ISSUE_AGE"] = issue_age * 100
    frame["CURRENT_AGE"] = _calculate_age(frame, issue_age, 0.62) * 100
    return frame


def _birth_date_add_years(birth_dt: datetime.date, years: int):
    """Add years to birth date"""
    return pd.to_datetime(
        {
            "year": birth_dt.dt.year + years,
            "month": birth_dt.dt.month,
            "day": birth_dt.dt.day,
        }
    )


@dispatch_function(key_parameters=("extract_type",))
def calculate_dates(extract_type: str, frame: pd.DataFrame, as_of_dt: datetime.date):
    """Calculate dates
    
    Parameters
    ----------
    extract_type : str
    frame : pd.DataFrame
    as_of_dt : datetime.date

    Returns
    -------
    pd.DataFrame
        If extract type is "disabled-lives" a DataFrame with columns BIRTH_DT, INCURRED_DT, and TERMINATION_DT. \n
        If extract type is "active-lives"  a DataFrame with columns BIRTH_DT and POLICY_START_DT.
 
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@calculate_dates.register(extract_type="disabled-lives")
def _(frame: pd.DataFrame, as_of_dt: datetime.date):

    # calculate birth date
    days_from_birth = frame["CURRENT_AGE"].values * 365.25

    frame["BIRTH_DT"] = as_of_dt - pd.to_timedelta(days_from_birth, unit="D").round("D")
    # move any birth on leap year to the 28th
    leap_dts = (frame["BIRTH_DT"].dt.month == 2) & (frame["BIRTH_DT"].dt.day == 29)
    frame.loc[leap_dts, "BIRTH_DT"] = frame[leap_dts]["BIRTH_DT"] - pd.offsets.Day(1)

    # calculate incurred date
    frame["INCURRED_DT"] = (
        frame["BIRTH_DT"] + pd.to_timedelta(frame["INCURRED_AGE"] * 365.25, unit="D")
    ).dt.round("D")

    term_dt = []
    for _, row in frame.iterrows():
        if row.IDI_BENEFIT_PERIOD[-1] == "M":
            mnt = int(row.IDI_BENEFIT_PERIOD.replace("M", ""))
            term_dt.append(
                row.INCURRED_DT
                + pd.DateOffset(days=row.ELIMINATION_PERIOD)
                + pd.DateOffset(months=mnt)
            )
        else:
            if row.IDI_BENEFIT_PERIOD == "LIFE":
                years = 120
            else:
                years = int(row.IDI_BENEFIT_PERIOD.replace("TO", ""))
            term_dt.append(row.BIRTH_DT + pd.DateOffset(years=years))

    frame["TERMINATION_DT"] = pd.Series(term_dt) - pd.DateOffset(days=1)
    return frame.drop(["CURRENT_AGE", "INCURRED_AGE", "TERMINATION_AGE"], axis=1)


@calculate_dates.register(extract_type="active-lives")
def _(frame: pd.DataFrame, as_of_dt: datetime.date):
    # calculate birth date
    days_from_birth = frame["CURRENT_AGE"].values * 365.25
    frame["BIRTH_DT"] = as_of_dt - pd.to_timedelta(days_from_birth, unit="D").round("D")

    # move any birth on leap year to the 28th
    leap_dts = (frame["BIRTH_DT"].dt.month == 2) & (frame["BIRTH_DT"].dt.day == 29)
    frame.loc[leap_dts, "BIRTH_DT"] = frame[leap_dts]["BIRTH_DT"] - pd.offsets.Day(1)

    # calculate issue date
    days_from_issue = frame["ISSUE_AGE"].values * 365.25
    frame["POLICY_START_DT"] = frame["BIRTH_DT"] + pd.to_timedelta(
        days_from_issue, unit="D"
    ).round("D")

    # calculate termination date for benefits with monthly benefit period
    cond_list = [
        (frame["IDI_BENEFIT_PERIOD"].str[:2] != "TO").values,
        (frame["IDI_BENEFIT_PERIOD"].str[-2:] == "65").values,
        (frame["IDI_BENEFIT_PERIOD"].str[-2:] == "67").values,
        (frame["IDI_BENEFIT_PERIOD"].str[-2:] == "70").values,
    ]

    choice_list = [
        _birth_date_add_years(frame["BIRTH_DT"], 65).values.astype(str),
        _birth_date_add_years(frame["BIRTH_DT"], 65).values.astype(str),
        _birth_date_add_years(frame["BIRTH_DT"], 67).values.astype(str),
        _birth_date_add_years(frame["BIRTH_DT"], 70).values.astype(str),
    ]

    frame["POLICY_END_DT"] = pd.to_datetime(
        np.select(cond_list, choice_list)
    ) - pd.DateOffset(days=1)

    frame["PREMIUM_PAY_TO_DT"] = frame["POLICY_END_DT"]

    return frame.drop(["CURRENT_AGE"], axis=1)


@dispatch_function(key_parameters=("extract_type",))
def finalize_extract(extract_type: str, frame: pd.DataFrame):
    """Finalize extract
    
    Parameters
    ----------
    extract_type : str
    frame : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        The final extract.
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@finalize_extract.register(extract_type="disabled-lives")
def _(frame: pd.DataFrame):
    frame["PAID_TO_DT"] = pd.NA
    return frame[disabled_life_columns]


@finalize_extract.register(extract_type="active-lives")
def _(frame: pd.DataFrame):
    return frame[active_lives_base_columns]
