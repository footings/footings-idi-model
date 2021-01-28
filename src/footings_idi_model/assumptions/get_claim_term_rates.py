from footings.utils import dispatch_function
from .stat_gaap.termination import _stat_gaap_ctr


@dispatch_function(key_parameters=("assumption_set", "model_mode",))
def get_ctr_table(assumption_set, model_mode, model_object):
    """Calculate claim termination rate (CTR) which varies by assumption_set (e.g., GAAP)
    and mode (i.e., ALR vs DLR).

    The CTR utilizes the select and ultimate tables required by the 2013 IDI Valuation Standard,
    as well as the required modifiers. The difference between running STAT vs GAAP is the use of
    margin. STAT includes it and GAAP does not.

    Parameters
    ----------
    assumption_set : str
        The name of the assumption set to use. Either stat, gaap, or best-estimate.
    model_mode : str
        The model mode to use. Either ALR, DLR, ALRCAT, or DLRCAT.
    model_object
        The model object to pass.

    Returns
    -------
    pd.DataFrame
        The passed DataFrame with an extra column for CTR.
    """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@get_ctr_table.register(
    assumption_set=("stat", "gaap"), model_mode=("ALR", "DLR", "ALRCAT", "DLRCAT")
)
def _(model_object):
    return _stat_gaap_ctr(
        frame=model_object.frame,
        idi_benefit_period=model_object.idi_benefit_period,
        idi_contract=model_object.idi_contract,
        idi_diagnosis_grp=model_object.idi_diagnosis_grp,
        idi_occupation_class=model_object.idi_occupation_class,
        gender=model_object.gender,
        elimination_period=model_object.elimination_period,
        age_incurred=model_object.age_incurred,
        cola_percent=model_object.cola_percent,
        model_mode=model_object.model_mode,
    )


@get_ctr_table.register(assumption_set="best-estimate", model_mode="DLR")
def _(model_object):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")


@get_ctr_table.register(assumption_set="best-estimate", model_mode="DLRCAT")
def _(model_object):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")
