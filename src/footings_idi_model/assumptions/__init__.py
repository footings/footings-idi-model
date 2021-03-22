import numpy as np
import pandas as pd
from footings.assumption_registry import assumption_registry, def_assumption_set

from .stat_gaap.incidence import get_incidence_rate
from .stat_gaap.interest import get_al_interest_rate, get_dl_interest_rate
from .stat_gaap.termination import get_ctr_select, get_ctr_ultimate


@assumption_registry
class idi_assumptions:
    """This is the collection of assumptions for the Footings IDI model."""

    GAAP = def_assumption_set("Assumption set for GAAP assumptions.")
    STAT = def_assumption_set("Assumption set for statutory assumptions.")
    BEST = def_assumption_set("Assumption set for best estimate assumptions.")

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
        cola_percent: str,
        model_mode: str,
    ):
        """The claim termination rate (ctr) is the probability that a person goes off disability.

        The CTR does not distinguish terminations between recoveries or mortality. In addition, the CTR
        is split into select rates (duration years 1 - 10) and ultimate rates (years 11+).

        | The select rate is a function of -
        |   Base rate (table lookup by IDI occupation class / gender / elimination period / age incurred / duration)
        |   x Benefit period modifier (table lookup by IDI benefit period / cola flag / duration year)
        |   x Cause modifier (table lookup by IDI contract type / gender / duration year / DLR vs ALR)
        |   x Contract modifier (table lookup by IDI contract type / duration year)
        |   x Diagnosis modifier (table lookup by diagnosis / duration year)
        |   x 1 - Margin adjustment (5% in duration year 1 and 15%  in durations 2+)

        """

        return get_ctr_select(
            age_incurred=age_incurred,
            idi_benefit_period=idi_benefit_period,
            idi_contract=idi_contract,
            idi_diagnosis_grp=idi_diagnosis_grp,
            idi_occupation_class=idi_occupation_class,
            gender=gender,
            elimination_period=elimination_period,
            cola_percent=cola_percent,
            model_mode=model_mode,
        )

    @STAT.register(name="Claim Termination Rate (CTR) - Ultimate")
    @GAAP.register(name="Claim Termination Rate (CTR) - Ultimate")
    def ctr_ultimate(idi_occupation_class: str, gender: str):
        """The claim termination rate (ctr) is the probability that a person goes off disability.

        The CTR does not distinguish terminations between recoveries or mortality. In addition, the CTR
        is split into select rates (duration years 1 - 10) and ultimate rates (years 11+).

        | The ultimate rate is a function of -
        |   Base rate (table lookup by IDI occupation class / gender / age attained)
        |   x 1 - Margin adjustment (15% in all durations)

        """
        return get_ctr_ultimate(idi_occupation_class=idi_occupation_class, gender=gender)

    @STAT.register(name="Claim Termination Rate (CTR)", bounded=True)
    @GAAP.register(name="Claim Termination Rate (CTR)", bounded=True)
    def ctr(
        self,
        frame: pd.DataFrame,
        age_incurred: str,
        idi_benefit_period: str,
        idi_contract: str,
        idi_diagnosis_grp: str,
        idi_occupation_class: str,
        gender: str,
        elimination_period: str,
        cola_percent: str,
        model_mode: str,
    ):
        """The claim termination rate (ctr) is the probability that a person goes off disability.

        | This assumption combines -
        |   1. the Select CTR (ctr_select) for claim duration years 1-10 and
        |   2. the Ultimate CTR (ctr_ultimate) for claim duration years 11+.
        """
        # Get select rates
        get_select = frame.DURATION_MONTH.min() <= 120
        if get_select:
            select = self.ctr_select(
                age_incurred=age_incurred,
                idi_benefit_period=idi_benefit_period,
                idi_contract=idi_contract,
                idi_diagnosis_grp=idi_diagnosis_grp,
                idi_occupation_class=idi_occupation_class,
                gender=gender,
                elimination_period=elimination_period,
                cola_percent=cola_percent,
                model_mode=model_mode,
            )

        # get ultimate rates
        get_ultimate = frame.DURATION_MONTH.max() > 120
        if get_ultimate:
            ult_rates = self.ctr_ultimate(
                idi_occupation_class=idi_occupation_class, gender=gender
            )
            ult_base = pd.DataFrame(
                {
                    "AGE_ATTAINED": frame.AGE_ATTAINED,
                    "DURATION_MONTH": frame.DURATION_MONTH,
                }
            )
            ultimate = ult_base.merge(ult_rates, how="left", on=["AGE_ATTAINED"])

        # return rates
        if get_select is True and get_ultimate is False:
            condlist = [select.PERIOD == "M", select.PERIOD == "Y"]
            choicelist = [select.SELECT_CTR, 1 - (1 - select.SELECT_CTR) ** (1 / 12)]
            ret = select.assign(CTR=np.select(condlist, choicelist))
        elif get_select is False and get_ultimate is True:
            ret = ultimate.assign(CTR=1 - (1 - ultimate.ULTIMATE_CTR) ** (1 / 12))
        else:
            ret = select.merge(ultimate, how="right", on=["DURATION_MONTH"])
            condlist = [
                ret.PERIOD == "M",
                ret.PERIOD == "Y",
                ret.PERIOD.isna(),
            ]
            choicelist = [
                ret.SELECT_CTR,
                1 - (1 - ret.SELECT_CTR) ** (1 / 12),
                1 - (1 - ret.ULTIMATE_CTR) ** (1 / 12),
            ]
        return ret.assign(CTR=np.select(condlist, choicelist))

    @BEST.register(name="Claim Termination Rate (CTR)")
    def ctr():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Incidence Rate")
    @GAAP.register(name="Incidence Rate")
    def incidence_rate(
        idi_contract: str,
        idi_occupation_class: str,
        idi_market: str,
        idi_benefit_period: str,
        tobacco_usage: str,
        elimination_period: int,
        gender: str,
    ):
        """Incidence rate is the probability of a policy holder becoming disabled.

        | The incidence rate is a function of -
        |   Base rate (table lookup by Acc vs Sick / IDI occupation class / gender / elimination period / age attained)
        |   x Benefit period modifier (table lookup by IDI occupation class / IDI benefit period / elimination period)
        |   x Contract modifier (table lookup by IDI contract)
        |   x Market modifier (table lookup by IDI market)
        |   x Tobacco modifier (table lookup by IDI occupation class / gender / elimination period / tobacco usage)

        """
        return get_incidence_rate(
            idi_contract=idi_contract,
            idi_occupation_class=idi_occupation_class,
            idi_market=idi_market,
            idi_benefit_period=idi_benefit_period,
            tobacco_usage=tobacco_usage,
            elimination_period=elimination_period,
            gender=gender,
        )

    @BEST.register(name="Incidence Rate")
    def incidence_rate():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Interest Rate - Active Lives")
    @GAAP.register(name="Interest Rate - Active Lives")
    def interest_rate_al(policy_start_dt):
        """STAT/GAAP active life (AL) interest rate assigned based on policy start date."""
        return get_al_interest_rate(policy_start_dt)

    @BEST.register(name="Interest Rate - Active Lives")
    def interest_rate_al():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Interest Rate - Disabled Lives")
    @GAAP.register(name="Interest Rate - Disabled Lives")
    def interest_rate_dl(incurred_dt):
        """STAT/GAAP interest rate assigned based on disability incurred year."""
        return get_dl_interest_rate(incurred_dt)

    @BEST.register(name="Interest Rate - Disabled Lives")
    def interest_rate_dl():
        """Not implemented yet."""
        raise NotImplementedError("Best estimate assumptions are not implemented yet.")

    @STAT.register(name="Mortality Rate")
    @GAAP.register(name="Mortality Rate")
    def mortality_rate():
        """Specify mortality table."""
        pass

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
