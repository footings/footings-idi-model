from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd

from footings import create_dispatch_function
from footings.library import create_frame, post_drop_columns, calculate_age

from ..assumptions.stat_gaap.termination import (
    contract_file,
    get_contract_modifier,
    benefit_period_file,
    get_benefit_period_modifier,
    diagnosis_file,
    get_diagnosis_modifier,
    cause_file,
    get_cause_modifier,
    select_file,
    get_select_ctr,
    ultimate_file,
    get_ultimate_ctr,
    margin_file,
    get_margin,
)
from ..assumptions.stat_gaap.interest import get_interest_rate


def sumprod_present_value(frame, columns):
    """Calculate the sumproduct present value of a list of columns in a frame."""
    return frame[columns].prod(axis=1).iloc[::-1].cumsum()


def _assign_end_date(frame):
    frame["DATE_ED"] = frame["DATE_BD"].shift(-1, fill_value=frame["DATE_BD"].iat[-1])
    return frame[frame.index != max(frame.index)]


def _calculate_exposure_and_benefit_factor(frame, start_pay_dt, termination_dt):

    dur_n_days = (frame["DATE_ED"] - frame["DATE_BD"]).dt.days
    dur_n_exposure = (termination_dt - frame["DATE_BD"].iat[-1]).days

    frame["EXPOSURE_FACTOR"] = 1.0
    if dur_n_days.iat[-1] != 0:
        exp_factor = max(0, min(1, dur_n_exposure / dur_n_days.iat[-1]))
        frame["EXPOSURE_FACTOR"].iat[-1] = exp_factor

    cond_list = [
        start_pay_dt > frame["DATE_ED"],
        (frame["DATE_BD"] <= start_pay_dt) & (start_pay_dt <= frame["DATE_ED"]),
    ]
    choice_list = [
        0.0,
        ((frame["DATE_ED"] - start_pay_dt).dt.days / dur_n_days).clip(
            lower=0.0, upper=1.0
        ),
    ]
    frame["BENEFIT_FACTOR"] = np.select(
        cond_list, choice_list, default=frame["EXPOSURE_FACTOR"].values
    )

    return frame


def _filter_frame(frame, valuation_dt):
    return frame[frame["DATE_ED"] >= valuation_dt]


def create_dlr_frame(
    valuation_dt,
    policy_id,
    claim_id,
    gender,
    birth_dt,
    incurred_dt,
    termination_dt,
    elimination_period,
    idi_contract,
    idi_benefit_period,
    idi_diagnosis_grp,
    idi_occupation_class,
    cola_percent,
):
    # build table
    fixed = {
        "frequency": "M",
        "col_date_nm": "DATE_BD",
        "duration_year": "DURATION_YEAR",
        "duration_month": "DURATION_MONTH",
    }
    start_pay_dt = incurred_dt + relativedelta(months=elimination_period / 30)
    frame = (
        create_frame(start_dt=incurred_dt, end_dt=termination_dt, **fixed)
        .pipe(_assign_end_date)
        .pipe(_filter_frame, valuation_dt)
        .pipe(_calculate_exposure_and_benefit_factor, start_pay_dt, termination_dt)
    )

    # assign main table attirbutes
    frame = frame.assign(
        POLICY_ID=policy_id,
        CLAIM_ID=claim_id,
        GENDER=gender,
        AGE_ATTAINED=lambda df: calculate_age(birth_dt, df["DATE_BD"], method="ACB"),
        AGE_INCURRED=lambda df: calculate_age(birth_dt, incurred_dt, method="ACB"),
        ELIMINATION_PERIOD=elimination_period,
        IDI_CONTRACT=idi_contract,
        IDI_BENEFIT_PERIOD=idi_benefit_period,
        IDI_DIAGNOSIS_GRP=idi_diagnosis_grp,
        IDI_OCCUPATION_CLASS=idi_occupation_class,
        COLA_FLAG="N" if cola_percent == 0 else "Y",
    )

    start_columns = [
        "DATE_BD",
        "DATE_ED",
        "DURATION_YEAR",
        "DURATION_MONTH",
    ]
    end_columns = set(frame.columns) - set(start_columns)
    return frame[start_columns + list(end_columns)]


def _apply_modifier(frame, modifier_frame, join_cols, fill=None):
    frame = frame.merge(modifier_frame, on=join_cols, how="left")
    if fill is not None:
        col_modifier = modifier_frame.columns[-1]
        frame.loc[frame["DURATION_YEAR"] < 11, col_modifier] = fill
    return frame


def _calculate_select_ctr_stat_gaap(frame, mode, apply_margin):
    select_ctr = get_select_ctr(select_file)
    select_join_cols = [
        "IDI_OCCUPATION_CLASS",
        "GENDER",
        "ELIMINATION_PERIOD",
        "AGE_INCURRED",
        "DURATION_MONTH",
    ]
    contract_modifier = get_contract_modifier(contract_file)
    contract_join_cols = ["DURATION_YEAR", "IDI_CONTRACT"]
    benefit_period_modifier = get_benefit_period_modifier(benefit_period_file)
    benefit_period_join_cols = ["IDI_BENEFIT_PERIOD", "COLA_FLAG", "DURATION_YEAR"]
    cause_modifier = get_cause_modifier(cause_file)
    cause_join_cols = ["IDI_CONTRACT", "GENDER", "DURATION_YEAR"]

    prod_cols = [
        "SELECT_CTR",
        "CONTRACT_MODIFIER",
        "BENEFIT_PERIOD_MODIFIER",
        "CAUSE_MODIFIER",
    ]
    if mode == "DLR":
        diagnosis_modifier = get_diagnosis_modifier(diagnosis_file)
        diagnosis_join_cols = ["DURATION_YEAR", "IDI_DIAGNOSIS_GRP"]
        prod_cols.append("DIAGNOSIS_MODIFIER")

    frame = (
        frame.merge(select_ctr, on=select_join_cols, how="left")
        .pipe(_apply_modifier, contract_modifier, contract_join_cols)
        .pipe(_apply_modifier, benefit_period_modifier, benefit_period_join_cols)
        .pipe(_apply_modifier, cause_modifier, cause_join_cols, fill=1)
    )

    if mode == "DLR":
        frame = frame.pipe(_apply_modifier, diagnosis_modifier, diagnosis_join_cols)

    if apply_margin is True:
        margin_adjustment = get_margin(margin_file)
        margin_join_cols = ["DURATION_YEAR"]
        prod_cols.append("MARGIN_ADJUSTMENT")
        frame = frame.pipe(_apply_modifier, margin_adjustment, margin_join_cols)

    frame.loc[frame["DURATION_YEAR"] < 11, "SELECT_MODIFIED_CTR"] = frame[prod_cols].prod(
        axis=1
    )
    frame.loc[frame["PERIOD"] == "Y", "SELECT_MODIFIED_CTR"] = 1 - (
        1 - frame["SELECT_MODIFIED_CTR"]
    ) ** (1 / 12)
    return frame


def _calculate_ultimate_ctr_stat_gaap(frame, apply_margin):
    ultimate_ctr = get_ultimate_ctr(ultimate_file)
    ultimate_join_cols = ["IDI_OCCUPATION_CLASS", "GENDER", "AGE_ATTAINED"]
    frame = frame.merge(ultimate_ctr, on=ultimate_join_cols, how="left")

    if apply_margin:
        frame["ULTIMATE_MODIFIED_CTR"] = 1 - (
            1 - frame["ULTIMATE_CTR"] * frame["MARGIN_ADJUSTMENT"]
        ) ** (1 / 12)
    else:
        frame["ULTIMATE_MODIFIED_CTR"] = 1 - (1 - frame["ULTIMATE_CTR"]) ** (1 / 12)
    return frame


def _calculate_ctr_stat_gaap(frame, mode, apply_margin):
    frame = frame.pipe(_calculate_select_ctr_stat_gaap, mode, apply_margin).pipe(
        _calculate_ultimate_ctr_stat_gaap, apply_margin
    )
    frame["CTR"] = frame["SELECT_MODIFIED_CTR"].combine_first(
        frame["ULTIMATE_MODIFIED_CTR"]
    )
    return frame


_BASE_DROP_COLUMNS = [
    "CONTRACT_MODIFIER",
    "BENEFIT_PERIOD_MODIFIER",
    "CAUSE_MODIFIER",
    "SELECT_CTR",
    "SELECT_MODIFIED_CTR",
    "ULTIMATE_CTR",
    "ULTIMATE_MODIFIED_CTR",
]
_DIAGNOSIS = ["DIAGNOSIS_MODIFIER"]
_MARGIN = ["MARGIN_ADJUSTMENT"]

calculate_ctr = create_dispatch_function(
    name="calculate_ctr", parameters=("assumption_set", "mode")
)


@calculate_ctr.register(assumption_set="gaap", mode="ALR")
@post_drop_columns(columns=_BASE_DROP_COLUMNS)
def _(frame):
    return _calculate_ctr_stat_gaap(frame, mode="ALR", apply_margin=False)


@calculate_ctr.register(assumption_set="gaap", mode="DLR")
@post_drop_columns(columns=_BASE_DROP_COLUMNS + _DIAGNOSIS)
def _(frame):
    return _calculate_ctr_stat_gaap(frame, mode="DLR", apply_margin=False)


@calculate_ctr.register(assumption_set="stat", mode="ALR")
@post_drop_columns(columns=_BASE_DROP_COLUMNS + _MARGIN)
def _(frame):
    return _calculate_ctr_stat_gaap(frame, mode="ALR", apply_margin=True)


@calculate_ctr.register(assumption_set="stat", mode="DLR")
@post_drop_columns(columns=_BASE_DROP_COLUMNS + _MARGIN + _DIAGNOSIS)
def _(frame):
    return _calculate_ctr_stat_gaap(frame, mode="DLR", apply_margin=True)


# @calculate_ctr.register(assumption_set="best-estimate", mode="ALR")
# def _(frame):
#     pass


# @calculate_ctr.register(assumption_set="best-estimate", mode="DLR")
# def _(frame):
#     pass


def calculate_cola_adjustment(frame, cola_percent, incurred_dt):
    """Calculate cola adjustment"""
    frame.loc[frame["DATE_BD"].dt.month == incurred_dt.month, "COLA_ADJUSTMENT"] = (
        1 + cola_percent
    )
    frame["COLA_ADJUSTMENT"] = frame["COLA_ADJUSTMENT"].fillna(1).cumprod()
    return frame


@post_drop_columns(columns=["COLA_ADJUSTMENT", "BENEFIT_FACTOR"])
def calculate_monthly_benefits(frame, benefit_amount):
    """Calculate monthly benefits"""
    prod_cols = ["BENEFIT_FACTOR", "COLA_ADJUSTMENT"]
    frame["BENEFIT_AMOUNT"] = frame[prod_cols].prod(axis=1).mul(benefit_amount).round(2)
    return frame


def calculate_lives(frame):
    """Calculate continuance"""
    frame["LIVES_ED"] = (1 - frame["CTR"]).cumprod()
    frame["LIVES_BD"] = frame["LIVES_ED"].shift(1, fill_value=1)
    frame["LIVES_MD"] = frame[["LIVES_BD", "LIVES_ED"]].mean(axis=1)
    return frame


@post_drop_columns(columns=["DAYS_TO_MD", "DAYS_TO_ED"])
def calculate_discount(frame, incurred_dt):
    """Calculate discount"""
    interest_rate = get_interest_rate(incurred_dt)
    min_duration = frame["DURATION_MONTH"].min()
    frame["DAYS_TO_ED"] = (frame["DURATION_MONTH"] - min_duration + 1) * 30
    frame["DAYS_TO_MD"] = frame["DAYS_TO_ED"] - 15
    frame["DISCOUNT_MD"] = 1 / (1 + interest_rate) ** (frame["DAYS_TO_MD"] / 360)
    frame["DISCOUNT_ED"] = 1 / (1 + interest_rate) ** (frame["DAYS_TO_ED"] / 360)
    frame["DISCOUNT_BD"] = frame["DISCOUNT_ED"].shift(1, fill_value=1)
    return frame


def calculate_pvfb(frame):
    """Calculate present value future benefits."""
    prod_columns = ["BENEFIT_AMOUNT", "LIVES_MD", "DISCOUNT_MD"]
    frame["PVFB_BD"] = sumprod_present_value(frame, prod_columns).round(2)
    frame["PVFB_ED"] = frame["PVFB_BD"].shift(-1, fill_value=0)
    return frame


_DLR_DROP_COLUMNS = ["WT_BD", "WT_ED", "PVFB_VD", "DISCOUNT_VD_ADJ", "LIVES_VD_ADJ"]


@post_drop_columns(columns=_DLR_DROP_COLUMNS)
def calculate_dlr(frame, valuation_dt):
    """Calculate DLR"""
    dur_n_days = (frame["DATE_ED"].iat[0] - frame["DATE_BD"].iat[0]).days
    frame["WT_BD"] = (frame["DATE_ED"].iat[0] - valuation_dt).days / dur_n_days
    frame["WT_ED"] = 1 - frame["WT_BD"]
    frame["PVFB_VD"] = frame[["WT_BD", "PVFB_BD"]].prod(axis=1) + frame[
        ["WT_ED", "PVFB_ED"]
    ].prod(axis=1)
    frame["DISCOUNT_VD_ADJ"] = 1 / (
        frame[["WT_BD", "DISCOUNT_BD"]].prod(axis=1)
        + frame[["WT_ED", "DISCOUNT_ED"]].prod(axis=1)
    )
    frame["LIVES_VD_ADJ"] = 1 / (
        frame[["WT_BD", "LIVES_BD"]].prod(axis=1)
        + frame[["WT_ED", "LIVES_ED"]].prod(axis=1)
    )
    prod_cols = ["PVFB_VD", "DISCOUNT_VD_ADJ", "LIVES_VD_ADJ"]
    frame["DLR"] = frame[prod_cols].prod(axis=1).round(2)
    frame["DATE_DLR"] = [
        valuation_dt + pd.DateOffset(months=period) for period in range(0, frame.shape[0])
    ]
    return frame


def to_output_format(frame):
    """To output format"""
    cols_select = [
        "POLICY_ID",
        "DATE_BD",
        "DATE_ED",
        "DURATION_YEAR",
        "DURATION_MONTH",
        "EXPOSURE_FACTOR",
        "BENEFIT_AMOUNT",
        "CTR",
        "LIVES_BD",
        "LIVES_MD",
        "LIVES_ED",
        "DISCOUNT_BD",
        "DISCOUNT_MD",
        "DISCOUNT_ED",
        "PVFB_BD",
        "PVFB_ED",
        "DATE_DLR",
        "DLR",
    ]
    return frame[cols_select]
