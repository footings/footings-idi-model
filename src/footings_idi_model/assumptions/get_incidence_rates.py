from footings.utils import dispatch_function

from .stat_gaap.incidence import _stat_gaap_incidence


@dispatch_function(key_parameters=("assumption_set",))
def get_incidence_rates(assumption_set, model_object):
    """ """
    msg = "No registered function based on passed paramters and no default function."
    raise NotImplementedError(msg)


@get_incidence_rates.register(assumption_set="stat")
def _(model_object):
    return _stat_gaap_incidence(
        idi_contract=model_object.idi_contract,
        idi_occupation_class=model_object.idi_occupation_class,
        idi_market=model_object.idi_market,
        idi_benefit_period=model_object.idi_benefit_period,
        tobacco_usage=model_object.tobacco_usage,
        elimination_period=model_object.elimination_period,
        gender=model_object.gender,
    )


@get_incidence_rates.register(assumption_set="gaap")
def _(model_object):
    return _stat_gaap_incidence(
        idi_contract=model_object.idi_contract,
        idi_occupation_class=model_object.idi_occupation_class,
        idi_market=model_object.idi_market,
        idi_benefit_period=model_object.idi_benefit_period,
        tobacco_usage=model_object.tobacco_usage,
        elimination_period=model_object.elimination_period,
        gender=model_object.gender,
    )


@get_incidence_rates.register(assumption_set="best-estimate")
def _(model_object):
    raise NotImplementedError("Best estimate assumptions are not implemented yet.")
