from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from inspect import getfullargspec
from functools import lru_cache

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
from ..policy_models import DLRDeterministicPolicyModel
from ..__init__ import __version__ as MOD_VERSION
from ..__init__ import __git_revision__ as GIT_REVISION


@lru_cache(maxsize=128)
def dlr_model_cache(**kwargs):
    return DLRDeterministicPolicyModel(**kwargs).run()


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


def _calculate_termination_date(
    incurred_dt: pd.Series,
    coverage_to_dt: pd.Series,
    birth_dt: pd.Timestamp,
    idi_benefit_period: str,
    elimination_period: int,
):
    if idi_benefit_period[-1] == "M":
        months = int(idi_benefit_period[:-1])
        termination_dt = (
            incurred_dt
            + pd.DateOffset(days=elimination_period)
            + pd.DateOffset(months=months)
        )
    elif idi_benefit_period[:2] == "TO":
        termination_dt = coverage_to_dt
    elif idi_benefit_period == "LIFE":
        termination_dt = pd.to_datetime(
            date(year=birth_dt.year + 120, month=birth_dt.month, day=birth_dt.day)
        )
    return termination_dt


def create_alr_frame(
    valuation_dt: pd.Timestamp,
    policy_id: str,
    coverage_id: str,
    gender: str,
    tobacco_usage: str,
    birth_dt: pd.Timestamp,
    policy_start_dt: pd.Timestamp,
    policy_end_dt: pd.Timestamp,
    elimination_period: int,
    idi_market: str,
    idi_contract: str,
    idi_benefit_period: str,
    idi_occupation_class: str,
    benefit_end_id: str,
    gross_premium: float,
    benefit_amount: float,
):
    """Create active life frame with a range from the policy issue date to termination date using 
    a yearly frequency.
    
    Parameters
    ----------
    valuation_dt : pd.Timestamp
    policy_id : str
    gender : str
    tobacco_usage : str
    birth_dt : pd.Timestamp
    policy_start_dt : pd.Timestamp
    policy_end_dt : pd.Timestamp
    elimination_period : int
    idi_market : str
    idi_contract : str
    idi_benefit_period : str
    idi_occupation_class : str
    benefit_end_id : str
    gross_premium : float
    benefit_amount : float
    
    Returns
    -------
    pd.DataFrame
        The DataFrame with the above Parameters as well as -
        - BEGIN_DT - the beginning date for a row
        - END_DT - the ending date for a row
        - DURATION_YEAR - the duration year for a row
    """
    # build table
    fixed = {"frequency": "Y", "col_date_nm": "DATE_BD", "duration_year": "DURATION_YEAR"}

    frame = (
        create_frame(start_dt=policy_start_dt, end_dt=policy_end_dt, **fixed)
        .pipe(_assign_end_date)
        .query("DATE_BD <= @policy_end_dt")
    )

    # assign main table attributes
    frame = frame.assign(
        MODEL_VERSION=MOD_VERSION,
        LAST_COMMIT=GIT_REVISION,
        RUN_DATE_TIME=pd.to_datetime("now"),
        POLICY_ID=policy_id,
        COVERAGE_ID=coverage_id,
        GENDER=gender,
        TOBACCO_USAGE=tobacco_usage,
        BIRTH_DT=birth_dt,
        AGE_ATTAINED=lambda df: calculate_age(birth_dt, df["DATE_BD"], method="ALB"),
        AGE_ISSUED=lambda df: calculate_age(birth_dt, policy_start_dt, method="ALB"),
        ELIMINATION_PERIOD=elimination_period,
        POLICY_END_DT=policy_end_dt,
        TERMINATION_DT=lambda df: _calculate_termination_date(
            df["DATE_BD"],
            df["POLICY_END_DT"],
            birth_dt,
            idi_benefit_period,
            elimination_period,
        ),
        IDI_MARKET=idi_market,
        IDI_CONTRACT=idi_contract,
        IDI_BENEFIT_PERIOD=idi_benefit_period,
        IDI_OCCUPATION_CLASS=idi_occupation_class,
        BENEFIT_END_ID=benefit_end_id,
        GROSS_PREMIUM=gross_premium,
        BENEFIT_AMOUNT=benefit_amount,
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


def calculate_discount(frame: pd.DataFrame, policy_start_dt: pd.Timestamp):
    """Calculate beginning, middle, and ending discount factor for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    incurred_dt : pd.Timestamp

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with additional columns DISCOUNT_BD, DISCOUNT_MD, and DISCOUNT_ED.        
    """
    interest_rate = get_interest_rate(policy_start_dt)
    frame["DISCOUNT_BD"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"] - 1)
    frame["DISCOUNT_MD"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"] - 0.5)
    frame["DISCOUNT_ED"] = 1 / (1 + interest_rate) ** (frame["DURATION_YEAR"])
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
def calculate_incidence_rate(frame: pd.DataFrame, idi_contract: str):
    """Calculate incidence rate for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    cause : str

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional column called INCIDENCE_RATE.        
    
    """
    if idi_contract == "AO":
        cause = "accident"
    elif idi_contract == "SO":
        cause = "sickness"
    else:
        cause = "combined"
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


def model_disabled_lives(
    frame: pd.DataFrame,
    assumption_set: str,
    birth_dt: pd.Timestamp,
    elimination_period: int,
    idi_benefit_period: str,
    cola_percent: float,
) -> dict:
    """Model a disabled life for each active duration.

    Parameters
    ----------
    assumptions_set : str
    birth_dt : pd.Timestamp
    elimination_period : int
    idi_benefit_period : str
    cola_percent : float
    
    Returns
    -------
    dict
        Key = (DURATION_YEAR, DATE_BD, DATE_ED)
        Value = results of dlr_deterministic_model
    """
    frame_use = frame.copy()
    frame_use.columns = [col.lower() for col in frame_use.columns]
    frame_use["valuation_dt"] = frame_use["date_bd"]
    frame_use["incurred_dt"] = frame_use["date_bd"]
    kwargs = set(getfullargspec(DLRDeterministicPolicyModel).kwonlyargs)
    cols = set(frame_use.columns)
    keep = kwargs.intersection(cols)
    records = frame_use[keep].to_dict(orient="records")

    def _run_model(assumption_set, cola_percent, **kwargs):
        return dlr_model_cache(
            assumption_set=assumption_set,
            cola_percent=cola_percent,
            claim_id="NA",
            idi_diagnosis_grp="AG",
            **kwargs,
        )

    results = (_run_model(assumption_set, cola_percent, **record) for record in records)
    return {
        (dur_year, bd, ed): result
        for dur_year, bd, ed, result in zip(
            frame["DURATION_YEAR"], frame["DATE_BD"], frame["DATE_ED"], results
        )
    }


@post_drop_columns(columns=["DLR"])
def calculate_claim_cost(
    frame: pd.DataFrame, modeled_disabled_lives: dict,
):
    """Calculate claim cost for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    model_disabled_life : dict

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional column called BENEFIT_COST.
    """
    dlrs = {k[0]: v["DLR"].iat[0] for k, v in modeled_disabled_lives.items()}
    frame["DLR"] = frame["DURATION_YEAR"].map(dlrs)
    frame["BENEFIT_COST"] = (frame["DLR"] * frame["INCIDENCE_RATE"]).round(2)
    return frame


def calculate_rop_payment_intervals(frame: pd.DataFrame, rop_return_frequency: int):
    """Calculate return of premium (ROP) payment intervals.

    Parameters
    ----------
    frame : pd.DataFrame
    rop_return_frequency : int

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional column called PAYMENT_INTERVAL.    
    """
    frame["PAYMENT_INTERVAL"] = (
        frame["DURATION_YEAR"].subtract(1).div(rop_return_frequency).astype(int)
    )
    return frame


def calculate_rop_future_disabled_claims(
    frame: pd.DataFrame,
    modeled_disabled_lives: dict,
    rop_future_claims_start_dt: pd.Timestamp,
) -> pd.DataFrame:
    """Calculate future claims for return of premium (ROP).
    
    Using the modeled disabled lives, take each active modeled duration and filter the projected
    payments to be less than or equal to the last date of the ROP payment interval. The data is 
    than concatenated into a single DataFrame.

    Parameters
    ----------
    modeled_disabled_lives : dict
    rop_future_claims_start_dt : pd.Timestamp

    Returns
    -------
    pd.DataFrame
        A DataFrame with the expected disabled payment by disabled and active duration.
    """
    max_payment_dates = (
        frame[["DURATION_YEAR", "PAYMENT_INTERVAL", "DATE_ED"]]
        .groupby(["PAYMENT_INTERVAL"], as_index=False)
        .transform(max)[["DATE_ED"]]
        .assign(DURATION_YEAR=frame["DURATION_YEAR"])
        .set_index(["DURATION_YEAR"])
        .to_dict()
        .get("DATE_ED")
    )

    cols = ["DATE_BD", "DATE_ED", "LIVES_MD", "BENEFIT_AMOUNT"]

    def model_payments(dur_year, dur_start_dt, dur_end_dt, frame):
        if dur_end_dt >= rop_future_claims_start_dt:
            if dur_start_dt >= rop_future_claims_start_dt:
                exp_factor = 1.0
            else:
                exp_factor = (rop_future_claims_start_dt - dur_start_dt) / (
                    dur_end_dt - dur_start_dt
                )
        else:
            exp_factor = 0
        return (
            frame[frame.DATE_ED <= max_payment_dates.get(dur_year)][cols]
            .rename(columns={"LIVES_MD": "DISABLED_LIVES_MD"})
            .assign(
                ACTIVE_DURATION_YEAR=dur_year,
                EXPOSURE_FACTOR=exp_factor,
                DISABLED_CLAIM_PAYMENTS=lambda df: df["EXPOSURE_FACTOR"]
                * df["DISABLED_LIVES_MD"]
                * df["BENEFIT_AMOUNT"],
            )
        )

    results = [
        model_payments(k[0], k[1], k[2], v) for k, v in modeled_disabled_lives.items()
    ]
    return pd.concat(results)


def calculate_rop_expected_claim_payments(
    frame: pd.DataFrame, rop_future_claims_frame: pd.DataFrame
) -> pd.DataFrame:
    """Calculate the expected claim payments for return of premium (ROP) for each active life duration.

    Parameters
    ----------
    frame : pd.DataFrame
    rop_future_claim_payments : dict

    Returns
    -------
    pd.DataFrame
        A DataFrame with the expected claim payment by active duration.
    """
    base_cols = ["PAYMENT_INTERVAL", "DURATION_YEAR", "LIVES_MD", "INCIDENCE_RATE"]
    base_frame = frame[base_cols]
    claim_payments = (
        rop_future_claims_frame.groupby(["ACTIVE_DURATION_YEAR"])[
            ["DISABLED_CLAIM_PAYMENTS"]
        ]
        .sum()
        .merge(
            base_frame,
            how="right",
            right_on="DURATION_YEAR",
            left_on="ACTIVE_DURATION_YEAR",
        )
        .assign(
            EXPECTED_CLAIM_PAYMENTS=lambda df: df["INCIDENCE_RATE"]
            * df["LIVES_MD"]
            * df["DISABLED_CLAIM_PAYMENTS"],
        )
    )

    add_cols = [
        "DISABLED_CLAIM_PAYMENTS",
        "EXPECTED_CLAIM_PAYMENTS",
    ]
    return claim_payments[base_cols + add_cols]


_ROP_DROP_COLS = [
    "PAYMENT_INTERVAL",
    "EXPECTED_CLAIM_PAYMENTS",
    "CLAIMS_PAID",
    "TOTAL_PREMIUM",
    "RETURN_PERCENTAGE",
]


def calculate_rop_benefits(
    frame: pd.DataFrame,
    rop_claims_paid: float,
    rop_return_percentage: float,
    rop_expected_claim_payments: pd.DataFrame,
    rop_future_claims_start_dt: pd.Timestamp,
):
    """Calculate benefit cost for each duration.
    
    Parameters
    ----------
    frame : pd.DataFrame
    rop_claims_paid : float
    rop_return_percentage : float
    rop_expected_claim_payments: pd.DataFrame
    rop_future_claims_start_dt : pd.Timestamp

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an additional columns called Benefit_COST.
    """
    expected_claim_payments = (
        rop_expected_claim_payments.groupby(["PAYMENT_INTERVAL"])[
            ["EXPECTED_CLAIM_PAYMENTS"]
        ]
        .sum()
        .to_dict()
        .get("EXPECTED_CLAIM_PAYMENTS")
    )

    max_int_rows = (
        frame.groupby(["PAYMENT_INTERVAL"])["DURATION_YEAR"].last().sub(1).astype(int)
    )

    frame["EXPECTED_CLAIM_PAYMENTS"] = 0
    frame.loc[max_int_rows, "EXPECTED_CLAIM_PAYMENTS"] = frame.loc[max_int_rows][
        "PAYMENT_INTERVAL"
    ].map(expected_claim_payments)

    criteria = (frame["DATE_BD"] <= rop_future_claims_start_dt) & (
        rop_future_claims_start_dt <= frame["DATE_ED"]
    )
    claim_row = frame[criteria]["PAYMENT_INTERVAL"]

    frame["CLAIMS_PAID"] = 0
    frame.loc[claim_row, "CLAIMS_PAID"] = rop_claims_paid

    total_premium = frame.groupby(["PAYMENT_INTERVAL"])["GROSS_PREMIUM"].sum().to_dict()
    frame["TOTAL_PREMIUM"] = 0
    frame.loc[max_int_rows, "TOTAL_PREMIUM"] = frame.loc[max_int_rows][
        "PAYMENT_INTERVAL"
    ].map(total_premium)

    frame["RETURN_PERCENTAGE"] = rop_return_percentage

    frame["BENEFIT_COST"] = (
        (
            frame["TOTAL_PREMIUM"] * frame["RETURN_PERCENTAGE"]
            - frame["EXPECTED_CLAIM_PAYMENTS"]
            - frame["CLAIMS_PAID"]
        )
        .clip(lower=0)
        .round(2)
    )
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
    pvfb_colums = ["LIVES_MD", "DISCOUNT_MD", "BENEFIT_COST"]
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
    choice_list = [frame["PVFB"].values, frame["PVFB"].values]
    frame["PVFNB"] = np.select(
        cond_list, choice_list, default=(frame["PVP"].values * nlp)
    ).round(2)
    return frame


def calculate_alr(frame: pd.DataFrame, valuation_dt: pd.Timestamp):
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

    frame = frame[frame["DATE_ED"] >= valuation_dt].copy()
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
    frame["ALR"] = (frame[alr_bd].prod(axis=1) + frame[alr_ed].prod(axis=1)).round(2)

    return frame
