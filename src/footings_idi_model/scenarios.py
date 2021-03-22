# from footings.scenario_registry import scenario_registry, def_attribute
#
#
# @scenario_registry
# class scenarios:
#     """This is the collection of scenarios to run for the Footings IDI model."""
#
#     ctr_modifier = def_attribute(default=1, description="")
#     interest_modifier = def_attribute(default=1, description="")
#     incidence_modifier = def_attribute(default=1, description="")
#     lapse_modifier = def_attribute(default=1, description="")
#
#
# @scenarios.register
# class interest_up:
#     interest_modifier = 1.1
#
#
# @scenarios.register
# class interest_down:
#     interest_modifier = 0.9
#
#
# @scenario_registry
# class scenarios:
#     """This is the collection of scenarios to run for the Footings IDI model."""
#
#     @scenario(base=True)
#     class base:
#         """Base class scenario."""
#
#         ctr_modifier = def_attribute(default=1, description="")
#         interest_modifier = def_attribute(default=1, description="")
#         incidence_modifier = def_attribute(default=1, description="")
#         lapse_modifier = def_attribute(default=1, description="")
#
#     @scenario
#     class interest_up:
#         """This is the interest up scenario."""
#
