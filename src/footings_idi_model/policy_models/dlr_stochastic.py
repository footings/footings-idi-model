from attr import attrs, attrib
import pandas as pd
import numpy as np
from footings import (
    define_asset,
    define_meta,
    define_modifier,
    define_parameter,
    Footing,
    step,
    model,
)
from footings.tools import post_drop_columns

from ..attributes import (
    param_assumption_set,
    param_n_simulations,
    param_seed,
    param_valuation_dt,
    meta_model_version,
    meta_last_commit,
    meta_run_date_time,
)
from ..functions.disabled_lives import (
    create_dlr_frame,
    calculate_ctr,
    calculate_cola_adjustment,
    calculate_monthly_benefits,
    calculate_discount,
    _sumprod_present_value,
)
from ..schemas import disabled_base_schema


OUTPUT_COLS = [
    "MODEL_VERSION",
    "LAST_COMMIT",
    "RUN_DATE_TIME",
    "POLICY_ID",
    "RUN",
    "DATE_BD",
    "DATE_ED",
    "DURATION_YEAR",
    "DURATION_MONTH",
    "BENEFIT_AMOUNT",
    "CTR",
    "DISCOUNT_BD",
    "DISCOUNT_MD",
    "DISCOUNT_ED",
    "BENEFITS_PAID",
    "PVFB_VD",
    "DISCOUNT_VD_ADJ",
    "DATE_DLR",
    "DLR",
]


STEPS = [
    "_create_frame",
    "_calculate_ctr",
    "_calculate_cola_adjustment",
    "_calculate_monthly_benefits",
    "_calculate_discount",
    "_calculate_val_date_items",
    "_simulate_benefits",
    "_to_output",
]


@model(steps=STEPS)
class DLRStochasticPolicyModel(Footing):
    """A policy model to calculate disabled life reserves (DLRs) using the 2013 individual
    disability insurance (IDI) valuation standard.

    The model is configured to use different assumptions sets - stat, gaap, or best-estimate.

    The key assumption underlying the model is -

    * `Termination Rates` - the probability of an individual going off claim.

    """

    n_simulations = param_n_simulations
    seed = param_seed
    valuation_dt = param_valuation_dt
    assumption_set = param_assumption_set
    policy_id = define_parameter(**disabled_base_schema["policy_id"])
    claim_id = define_parameter(**disabled_base_schema["claim_id"])
    gender = define_parameter(**disabled_base_schema["gender"])
    birth_dt = define_parameter(**disabled_base_schema["birth_dt"])
    incurred_dt = define_parameter(**disabled_base_schema["incurred_dt"])
    termination_dt = define_parameter(**disabled_base_schema["termination_dt"])
    elimination_period = define_parameter(**disabled_base_schema["elimination_period"])
    idi_contract = define_parameter(**disabled_base_schema["idi_contract"])
    idi_benefit_period = define_parameter(**disabled_base_schema["idi_benefit_period"])
    idi_diagnosis_grp = define_parameter(**disabled_base_schema["idi_diagnosis_grp"])
    idi_occupation_class = define_parameter(
        **disabled_base_schema["idi_occupation_class"]
    )
    cola_percent = define_parameter(**disabled_base_schema["cola_percent"])
    benefit_amount = define_parameter(**disabled_base_schema["benefit_amount"])
    ctr_modifier = define_modifier(default=1.0)
    interst_modifier = define_modifier(default=1.0)
    frame = define_asset(dtype=pd.DataFrame)
    model_version = meta_model_version
    last_commit = meta_last_commit
    run_date_time = meta_run_date_time

    @step(
        uses=[
            "valuation_dt",
            "policy_id",
            "claim_id",
            "gender",
            "birth_dt",
            "incurred_dt",
            "termination_dt",
            "elimination_period",
            "idi_contract",
            "idi_benefit_period",
            "idi_diagnosis_grp",
            "idi_occupation_class",
            "cola_percent",
        ],
        impacts=["frame"],
    )
    def _create_frame(self):
        self.frame = create_dlr_frame(
            valuation_dt=self.valuation_dt,
            policy_id=self.policy_id,
            claim_id=self.claim_id,
            gender=self.gender,
            birth_dt=self.birth_dt,
            incurred_dt=self.incurred_dt,
            termination_dt=self.termination_dt,
            elimination_period=self.elimination_period,
            idi_contract=self.idi_contract,
            idi_benefit_period=self.idi_benefit_period,
            idi_diagnosis_grp=self.idi_diagnosis_grp,
            idi_occupation_class=self.idi_occupation_class,
            cola_percent=self.cola_percent,
        )

    @step(uses=["frame", "assumption_set"], impacts=["frame"])
    def _calculate_ctr(self):
        self.frame = calculate_ctr(
            frame=self.frame, assumption_set=self.assumption_set, mode="DLR",
        )

    @step(uses=["frame", "cola_percent"], impacts=["frame"])
    def _calculate_cola_adjustment(self):
        self.frame = calculate_cola_adjustment(
            frame=self.frame, cola_percent=self.cola_percent
        )

    @step(uses=["frame", "benefit_amount"], impacts=["frame"])
    def _calculate_monthly_benefits(self):
        self.frame = calculate_monthly_benefits(
            frame=self.frame, benefit_amount=self.benefit_amount
        )

    @step(uses=["frame", "incurred_dt"], impacts=["frame"])
    def _calculate_discount(self):
        self.frame = calculate_discount(frame=self.frame, incurred_dt=self.incurred_dt)

    @step(uses=["frame"], impacts=["frame"])
    def _calculate_val_date_items(self):
        """Calculate benefits paid using simulated inforce.

        Returns
        -------
        pd.DataFrame
            The DataFrame with an added column BENEFITS_PAID.
        """
        cols_bd, cols_ed = ["WT_BD", "DISCOUNT_BD"], ["WT_ED", "DISCOUNT_ED"]
        self.frame["DISCOUNT_VD_ADJ"] = 1 / (
            self.frame[cols_bd].prod(axis=1) + self.frame[cols_ed].prod(axis=1)
        )
        self.frame["DATE_DLR"] = [
            self.valuation_dt + pd.DateOffset(months=period)
            for period in range(0, self.frame.shape[0])
        ]

    @step(uses=["frame", "seed", "n_simulations"], impacts=["frame"])
    def _simulate_benefits(self):
        """Simulate benefits paid for each simulation.

        Returns
        -------
        pd.DataFrame
        """
        np.random.seed(seed=self.seed)
        cols = list(self.frame.columns)
        cols_add = [
            "RANDOM",
            "TEMP_INFORCE",
            "INFORCE",
            "BENEFITS_PAID",
            "PVFB_VD",
            "DLR",
        ]

        def simulate(df, run):
            rows = df.shape[0]
            df = df.copy()
            df["RUN"] = run
            df["RANDOM"] = np.random.uniform(size=rows)
            df["TEMP_INFORCE"] = np.select([df["CTR"] > df["RANDOM"]], [0], default=1.0)
            df["TEMP_CUM"] = df["TEMP_INFORCE"].cumsum()
            df.loc[(df["TEMP_CUM"] != df.index.values + 1), "TEMP_INFORCE"] = 0.0
            condlist = [(df["TEMP_INFORCE"].shift(1) == 1) & (df["TEMP_INFORCE"] == 0)]
            df["INFORCE"] = np.select(condlist, [0.5], default=df["TEMP_INFORCE"])
            df["BENEFITS_PAID"] = df["BENEFIT_AMOUNT"] * df["INFORCE"]
            prod_columns = ["BENEFITS_PAID", "DISCOUNT_MD"]
            df["PVFB_BD"] = _sumprod_present_value(df, prod_columns).round(2)
            df["PVFB_ED"] = df["PVFB_BD"].shift(-1, fill_value=0)
            cols_bd, cols_ed = ["WT_BD", "PVFB_BD"], ["WT_ED", "PVFB_ED"]
            df["PVFB_VD"] = df[cols_bd].prod(axis=1) + df[cols_ed].prod(axis=1)
            df["DLR"] = df[["PVFB_VD", "DISCOUNT_VD_ADJ"]].prod(axis=1).round(2)

            return df[["RUN"] + cols + cols_add]

        self.frame = pd.concat(
            [simulate(self.frame, n) for n in range(1, self.n_simulations + 1)]
        )

    @step(uses=["frame"], impacts=["frame"])
    def _to_output(self):
        """Create model output.

        Returns
        -------
        pd.DataFrame
            The final frame.
        """
        return self.frame[OUTPUT_COLS]
