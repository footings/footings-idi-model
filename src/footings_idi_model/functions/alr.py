from datetime import timedelta, date
from inspect import getfullargspec

import numpy as np
import pandas as pd

from footings import dispatch_function
from footings.tools import create_frame, post_drop_columns, calculate_age

from ..assumptions.stat_gaap.incidence import (
    contract_file,
    get_contract_modifier,
    benefit_period_file,
    get_benefit_period_modifier,
    market_file,
    get_market_modifier,
    tobacco_file,
    get_tobacco_modifier,
    incidence_file,
    get_base_incidence,
    margin_file,
    get_margin,
)
from ..assumptions.stat_gaap.interest import get_interest_rate
from ..assumptions.stat_gaap.lapse import get_lapses, get_age_band
from ..assumptions.mortality import get_mortality
from ..policy_models import dlr_deterministic_model


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


def create_alr_frame(
    valuation_dt: pd.Timestamp,
    policy_id: str,
    gender: str,
    tobacco_usage: str,
    birth_dt: pd.Timestamp,
    issue_dt: pd.Timestamp,
    termination_dt: pd.Timestamp,
    elimination_period: int,
    idi_market: str,
    idi_contract: str,
    idi_benefit_period: str,
    idi_occupation_class: str,
):
    """Create active life frame with a range from the policy issue date to termination date using 
    a yearly frequency.
    
    Parameters
    ----------
    valuation_dt: pd.Timestamp
    policy_id: str
    gender: str
    tobacco_usage: str
    birth_dt: pd.Timestamp
    issue_dt: pd.Timestamp
    termination_dt: pd.Timestamp
    elimination_period: int
    idi_market: str
    idi_contract: str
    idi_benefit_period: str
    idi_occupation_class: str
    
    Returns
    -------
    pd.DataFrame
        The DataFrame with the above Parameters as well as -
        - BEGIN_DT - the begining date for a row
        - END_DT - the ending date for a row
        - DURATION_YEAR - the duration year for a row
    """
    # build table
    fixed = {
        "frequency": "Y",
        "col_date_nm": "DATE_BD",
        "duration_year": "DURATION_YEAR",
    }

    frame = (
        create_frame(start_dt=issue_dt, end_dt=termination_dt, **fixed)
        .pipe(_assign_end_date)
        .query("DATE_BD < @termination_dt")
    )

    # assign main table attributes
    frame = frame.assign(
        POLICY_ID=policy_id,
        GENDER=gender,
        TOBACCO_USAGE=tobacco_usage,
        BIRTH_DT=birth_dt,
        AGE_ATTAINED=lambda df: calculate_age(birth_dt, df["DATE_BD"], method="ALB"),
        AGE_ISSUED=lambda df: calculate_age(birth_dt, issue_dt, method="ALB"),
        ELIMINATION_PERIOD=elimination_period,
        TERMINATION_DT=termination_dt,
        IDI_MARKET=idi_market,
        IDI_CONTRACT=idi_contract,
        IDI_BENEFIT_PERIOD=idi_benefit_period,
        IDI_OCCUPATION_CLASS=idi_occupation_class,
    )

    start_columns = ["DATE_BD", "DATE_ED", "DURATION_YEAR"]
    return frame[start_columns + list(frame.columns[3:])]


def _calculate_lives(frame: pd.DataFrame, persistency_src: str):
    if persistency_src in ["01CSO", "17CSO", "58CSO", "80CSO"]:
        pers_rate = get_mortality(persistency_src).drop(["BASIS"], axis=1)
        frame = frame.merge(pers_rate, on=["GENDER", "AGE_ATTAINED"], how="left")
        frame["LIVES_ED"] = (1 - frame["MORTALITY_RATE"]).cumprod()
    elif persistency_src in ["gr", "non-gr"]:
        pers_rate = get_lapses(persistency_src)
        age_band = get_age_band()
        frame = frame.merge(age_band, on=["AGE_ISSUED"], how="left").merge(
            pers_rate, on=["AGE_BAND", "DURATION_YEAR"], how="left"
        )
        frame["LIVES_ED"] = (1 - frame["LAPSE_RATE"]).cumprod()

    frame["LIVES_BD"] = frame["LIVES_ED"].shift(1, fill_value=1)
    frame["LIVES_MD"] = (frame["LIVES_BD"] + frame["LIVES_ED"]) / 2

    return frame


@dispatch_function(key_parameters=("assumption_set",))
def calculate_lives(assumption_set: str, frame: pd.DataFrame):
    """Calculate lives for each duration.

    Parameters
    ----------
    assumption_set : str
    frame : pd.DataFrame
    
    Returns
    -------
    pd.DataFrame
        The passed DataFrame with additional columns LIVES_BD, LIVES_MD, and LIVES_ED.
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@calculate_lives.register(assumption_set="stat")
def _(frame):
    return _calculate_lives(frame, persistency_src="01CSO")


@calculate_lives.register(assumption_set="gaap")
@post_drop_columns(columns=["AGE_BAND"])
def _(frame):
    return _calculate_lives(frame, persistency_src="gr")


def calculate_discount(frame: pd.DataFrame, issue_dt: pd.Timestamp):
    """Calculate begining, middle, and ending discount factor for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    incurred_dt : pd.Timestamp

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with additional columns DISCOUNT_BD, DISCOUNT_MD, and DISCOUNT_ED.        
    """
    interest_rate = get_interest_rate(issue_dt)
    frame["DISCOUNT_BD"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"] - 1)
    frame["DISCOUNT_MD"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"] - 0.5)
    frame["DISCOUNT_ED"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"])
    return frame


def calculate_cola_adjustment(frame: pd.DataFrame, cola_percent: float):
    """Calculate cost of living adjustment adjustment.
    
    Parameters
    ----------
    frame : pd.DataFrame
    cola_percent : float

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional column called COLA_ADJUSTMENT.
    """
    frame["COLA_PERCENT"] = cola_percent
    frame.loc[frame["DURATION_YEAR"] > 1, "COLA_ADJUSTMENT"] = 1 + cola_percent
    frame["COLA_ADJUSTMENT"] = frame["COLA_ADJUSTMENT"].fillna(1).cumprod()
    return frame


@post_drop_columns(columns=["COLA_ADJUSTMENT"])
def calculate_benefit_amount(frame: pd.DataFrame, benefit_amount: float):
    frame["BENEFIT_AMOUNT"] = (frame["COLA_ADJUSTMENT"] * benefit_amount).round(2)
    return frame


_INCIDENCE_DROP_COLUMNS = [
    "INCIDENCES",
    "BENEFIT_PERIOD_MODIFIER",
    "CONTRACT_MODIFIER",
    "MARKET_MODIFIER",
    "TOBACCO_MODIFIER",
    "MARGIN_ADJUSTMENT",
    "TOBACCO_USAGE",
]


@post_drop_columns(columns=_INCIDENCE_DROP_COLUMNS)
def calculate_incidence_rate(frame: pd.DataFrame, cause: str):
    """Calculate indcidence rate for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    cause : str

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional column called INCIDENCE_RATE.        
    
    """
    base_incidence = get_base_incidence(incidence_file, cause)
    base_join_cols = [
        "IDI_OCCUPATION_CLASS",
        "GENDER",
        "ELIMINATION_PERIOD",
        "AGE_ATTAINED",
    ]
    benefit_period_modifier = get_benefit_period_modifier(benefit_period_file)
    benefit_period_join_cols = [
        "IDI_OCCUPATION_CLASS",
        "IDI_BENEFIT_PERIOD",
        "ELIMINATION_PERIOD",
    ]
    contract_modifier = get_contract_modifier(contract_file)
    contract_join_cols = ["IDI_CONTRACT"]
    market_modifier = get_market_modifier(market_file)
    market_join_cols = ["IDI_MARKET"]
    tobacco_modifier = get_tobacco_modifier(tobacco_file)
    tobacco_join_cols = [
        "IDI_OCCUPATION_CLASS",
        "GENDER",
        "ELIMINATION_PERIOD",
        "TOBACCO_USAGE",
    ]
    margin_adjustment = get_margin(margin_file)
    margin_join_cols = ["DURATION_YEAR"]
    frame = (
        frame.merge(base_incidence, on=base_join_cols, how="left")
        .merge(benefit_period_modifier, on=benefit_period_join_cols, how="left")
        .merge(contract_modifier, on=contract_join_cols, how="left")
        .merge(market_modifier, on=market_join_cols, how="left")
        .merge(tobacco_modifier, on=tobacco_join_cols, how="left")
        .merge(margin_adjustment, on=margin_join_cols, how="left")
    )
    prod_cols = [
        "INCIDENCES",
        "BENEFIT_PERIOD_MODIFIER",
        "CONTRACT_MODIFIER",
        "MARKET_MODIFIER",
        "TOBACCO_MODIFIER",
        "MARGIN_ADJUSTMENT",
    ]
    frame["INCIDENCE_RATE"] = frame[prod_cols].prod(axis=1).div(1000)
    return frame


def _calculate_termination_date(
    incurred_dt: pd.Timestamp,
    coverage_to_dt: pd.Timestamp,
    birth_dt: pd.Timestamp,
    idi_benefit_period: str,
):
    if idi_benefit_period[-1] == "M":
        months = int(idi_benefit_period[:-1])
        termination_dt = incurred_dt + pd.to_timedelta(months, unit="M")
    elif idi_benefit_period[:2] == "TO":
        termination_dt = coverage_to_dt
    elif idi_benefit_period[:2] == "LIFETIME":
        termination_dt = date(
            year=birth_dt.year + 120, month=birth_dt.month, day=birth_dt.day
        )
    return termination_dt


_CLAIM_COST_DROP_COLUMNS = [
    "BIRTH_DT",
    "TERMINATION_DT",
    "GENDER",
    "AGE_ATTAINED",
    "AGE_ISSUED",
    "COLA_PERCENT",
    "ELIMINATION_PERIOD",
    "IDI_OCCUPATION_CLASS",
    "IDI_BENEFIT_PERIOD",
    "IDI_CONTRACT",
    "IDI_MARKET",
]


@post_drop_columns(columns=_CLAIM_COST_DROP_COLUMNS)
def calculate_claim_cost(
    frame: pd.DataFrame,
    assumption_set: str,
    birth_dt: pd.Timestamp,
    idi_benefit_period: str,
):
    """Calculate claim cost for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    assumption_set : pd.DataFrame
    birth_dt : pd.Timestamp
    idi_benefit_period : str

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional columns called DLR and CLAIM_COST.
    """
    frame_use = frame.copy()
    frame_use.columns = [col.lower() for col in frame_use.columns]
    frame_use = frame_use.assign(
        valuation_dt=lambda df: df["date_bd"],
        incurred_dt=lambda df: df["date_bd"],
        termination_dt=lambda df: _calculate_termination_date(
            df["incurred_dt"], df["termination_dt"], birth_dt, idi_benefit_period
        ),
    )
    kwargs = set(getfullargspec(dlr_deterministic_model).kwonlyargs)
    cols = set(frame_use.columns)
    keep = kwargs.intersection(cols)
    records = frame_use[keep].to_dict(orient="records")
    claim_list = []
    for record in records:
        model_kwargs = {
            "assumption_set": assumption_set,
            "claim_id": "NA",
            "idi_diagnosis_grp": "AG",
            **record,
        }
        claim_list.append(dlr_deterministic_model(**model_kwargs).run()["DLR"].iat[0])
    frame["DLR"] = claim_list
    frame["CLAIM_COST"] = (frame["DLR"] * frame["INCIDENCE_RATE"]).round(2)
    return frame


@post_drop_columns(columns=["PVFB_PROD"])
def calculate_pvfb(frame: pd.DataFrame):
    """Calculate present value future benefits (PVFB).
    
    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
        The passed DataFrame with an additional columns called PVFB.
    """
    pvfb_colums = ["LIVES_MD", "DISCOUNT_MD", "CLAIM_COST"]
    frame["PVFB_PROD"] = frame[pvfb_colums].prod(axis=1)
    frame["PVFB"] = frame["PVFB_PROD"].iloc[::-1].cumsum().round(2)
    return frame


@post_drop_columns(columns=["PAY_FLAG"])
def calculate_pvnfb(frame: pd.DataFrame, net_benefit_method: str):  # premium_pay_to_age
    """Calculate present value net future benefits (PVNFB).
    
    Parameters
    ----------
    frame : pd.DataFrame
    net_benefit_method : str

    Returns
    -------
        The passed DataFrame with an additional columns called PVNFB.
    """
    frame["PAY_FLAG"] = 1
    pvp_cols = ["PAY_FLAG", "LIVES_BD", "DISCOUNT_BD"]
    frame["PVP"] = frame[pvp_cols].prod(axis=1).iloc[::-1].cumsum()
    pvp = frame["PVP"].iat[0]

    if net_benefit_method == "NLP":
        pvfb = frame["PVFB"].iat[0]
    elif net_benefit_method == "PT1":
        pvfb = frame[frame.DURATION_YEAR > 1]["PVFB"].iat[0]
    elif net_benefit_method == "PT2":
        pvfb = frame[frame.DURATION_YEAR > 2]["PVFB"].iat[0]
    else:
        msg = f"The net_benefit_method [{net_benefit_method}] is not recognzied. See Documentation."
        raise ValueError(msg)

    nlp = pvfb / pvp
    duration = frame["DURATION_YEAR"].values
    cond_list = [
        np.array((net_benefit_method == "PT1") & (duration <= 1), dtype=bool),
        np.array((net_benefit_method == "PT2") & (duration <= 2), dtype=bool),
    ]
    choice_list = [
        frame["PVFB"].values,
        frame["PVFB"].values,
    ]
    frame["PVFNB"] = np.select(
        cond_list, choice_list, default=(frame["PVP"].values * nlp)
    ).round(2)
    return frame


def calculate_alr_from_issue(frame: pd.DataFrame):
    """Calculate active life reserves (ALR) from issue.
    
    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
        The passed DataFrame with additional columns called ALR_BD and ALR_ED.
    """
    frame["ALR_BD"] = (
        (frame["PVFB"] - frame["PVFNB"]).div(frame["DISCOUNT_BD"]).clip(lower=0)
    ).round(2)
    frame["ALR_ED"] = frame["ALR_BD"].shift(-1, fill_value=0)
    return frame


def calculate_alr_from_valuation_date(frame: pd.DataFrame, valuation_dt: pd.Timestamp):
    """Normalize ALR as of valuation date.
    
    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
        The passed DataFrame with an additional column called ALR.
    """
    frame = frame[frame["DATE_BD"] >= valuation_dt].copy()
    frame["DATE_ALR"] = pd.to_datetime(
        [
            valuation_dt + pd.DateOffset(years=period)
            for period in range(0, frame.shape[0])
        ]
    )

    dur_n_days = (frame["DATE_ED"].iat[0] - frame["DATE_BD"].iat[0]).days
    frame["WT_BD"] = (frame["DATE_ED"].iat[0] - valuation_dt).days / dur_n_days
    frame["WT_ED"] = 1 - frame["WT_BD"]

    alr_bd, alr_ed = ["WT_BD", "ALR_BD"], ["WT_ED", "ALR_ED"]
    frame["ALR_VD"] = frame[alr_bd].prod(axis=1) + frame[alr_ed].prod(axis=1)

    dis_bd, dis_ed = ["WT_BD", "DISCOUNT_BD"], ["WT_ED", "DISCOUNT_ED"]
    frame["DISCOUNT_VD_ADJ"] = 1 / (
        frame[dis_bd].prod(axis=1) + frame[dis_ed].prod(axis=1)
    )

    lives_bd, lives_ed = ["WT_BD", "LIVES_BD"], ["WT_ED", "LIVES_ED"]
    frame["LIVES_VD_ADJ"] = 1 / (
        frame[lives_bd].prod(axis=1) + frame[lives_ed].prod(axis=1)
    )

    prod_cols = ["ALR_VD", "DISCOUNT_VD_ADJ", "LIVES_VD_ADJ"]
    frame["ALR"] = frame[prod_cols].prod(axis=1).round(2)
    return frame


def to_output_format(frame: pd.DataFrame):
    """Return the calculated frame with attributes covering the policy, duration, and ALR.

    Parameters
    ----------
    frame : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        The final DataFrame. 
    """
    cols_order = [
        "POLICY_ID",
        "DATE_BD",
        "DATE_ED",
        "DURATION_YEAR",
        "LIVES_BD",
        "LIVES_MD",
        "LIVES_ED",
        "DISCOUNT_BD",
        "DISCOUNT_MD",
        "DISCOUNT_ED",
        "BENEFIT_AMOUNT",
        "INCIDENCE_RATE",
        "DLR",
        "CLAIM_COST",
        "PVFB",
        "PVP",
        "ALR_BD",
        "ALR_ED",
        "DATE_ALR",
        "ALR",
    ]
    return frame[cols_order]
