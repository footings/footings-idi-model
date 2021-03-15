from footings.assumption_registry import assumption_registry, def_assumption_set

from .stat_gaap.incidence import _stat_gaap_incidence
from .stat_gaap.termination import _stat_gaap_ctr


@assumption_registry
class idi_assumptions:
    """This is the collection of assumptions for the Footings IDI model."""

    GAAP = def_assumption_set("GAAP assumption set.")
    STAT = def_assumption_set("Stat assumption set.")
    BEST = def_assumption_set("Best estimate assumption set.")

    @STAT.register(name="Claim Termination Rate (CTR) - Select")
    @GAAP.register(name="Claim Termination Rate (CTR) - Select")
    def ctr_select(
        age_incurred: str,
        idi_benefit_period: str,
        idi_contract: str,
        idi_diagnosis_grp: str,
        idi_occupation_class: str,
        gender: str,
        elimination_period: str,
        cola_flag: str,
        model_mode: str,
    ):
        """The claim termination rate (ctr) is the probability that a person goes off disability.

        The CTR does not distinguish terminations between recoveries or mortality. In addition, the CTR
        is split into select rates (duration years 1 - 10) and ultimate rates (years 11+).

        The select rate formula is -

        | Base rate (table lookup by IDI occupation class / gender / elimination period / age incurred / duration)
        | x Benefit period modifier (table lookup by IDI benefit period / cola flag / duration year)
        | x Cause modifier (table lookup by IDI contract type / gender / duration year / DLR vs ALR)
        | x Contract modifier (table lookup by IDI contract type / duration year)
        | x Diagnosis modifier (table lookup by diagnosis / duration year)
        | x 1 - Margin adjustment (5% in duration year 1 and 15%  in durations 2+)

        """
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

    @STAT.register(name="Claim Termination Rate (CTR) - Ultimate")
    @GAAP.register(name="Claim Termination Rate (CTR) - Ultimate")
    def ctr_ultimate(idi_occupation_class: str, gender: str):
        """The claim termination rate (ctr) is the probability that a person goes off disability.

        The CTR does not distinguish terminations between recoveries or mortality. In addition, the CTR
        is split into select rates (duration years 1 - 10) and ultimate rates (years 11+).

        The ultimate rate formula is -

        | Base rate (table lookup by IDI occupation class / gender / age attained)
        | x 1 - Margin adjustment (15% in all durations)

        """
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

    @BEST.register(name="Claim Termination Rate (CTR)")
    def claim_term_rate():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Incidence Rate")
    @GAAP.register(name="Incidence Rate")
    def incidence_rate(model_object):
        """Incidence rate is the probability of a policy holder becoming disabled.

        The incidence rate formula is -

        | Base rate (table lookup by Acc vs Sick / IDI occupation class / gender / elimination period / age attained)
        | x Benefit period modifier (table lookup by IDI occupation class / IDI benefit period / elimination period)
        | x Contract modifier (table lookup by IDI contract)
        | x Market modifier (table lookup by IDI market)
        | x Tobacco modifier (table lookup by IDI occupation class / gender / elimination period / tobacco usage)

        """
        return _stat_gaap_incidence(
            idi_contract=model_object.idi_contract,
            idi_occupation_class=model_object.idi_occupation_class,
            idi_market=model_object.idi_market,
            idi_benefit_period=model_object.idi_benefit_period,
            tobacco_usage=model_object.tobacco_usage,
            elimination_period=model_object.elimination_period,
            gender=model_object.gender,
        )

    @BEST.register(name="Incidence Rate")
    def incidence_rate():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Mortality Rate")
    @GAAP.register(name="Mortality Rate")
    def mortality_rate():
        """Specify mortality table."""

    @BEST.register(name="Mortality Rate")
    def mortality_rate():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Lapse Rate")
    @GAAP.register(name="Lapse Rate")
    def lapse_rate():
        """Specify lapse table."""
        pass

    @BEST.register(name="Lapse Rate")
    def lapse_rate():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")


class Test:
    @staticmethod
    def ctr_select(x):
        """This get ctr select assumption."""

    @staticmethod
    def ctr_ultimate(x):
        """This gets ctr ultimate."""
