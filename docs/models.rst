
======
Models
======

Policy Models
=============

|

DLR Deterministic
-----------------

.. autofunction:: footings_idi_model.policy_models.dlr_deterministic_model

|

.. autofunction:: footings_idi_model.functions.disabled_lives.create_dlr_frame
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_ctr
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_cola_adjustment
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_monthly_benefits
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_lives
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_discount
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_pvfb
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_dlr
.. autofunction:: footings_idi_model.functions.disabled_lives.to_output_format

|

DLR Stochastic
-----------------

.. autofunction:: footings_idi_model.policy_models.dlr_stochastic_model

|

.. autofunction:: footings_idi_model.functions.disabled_lives.create_dlr_frame
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_ctr
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_cola_adjustment
.. autofunction:: footings_idi_model.functions.disabled_lives.calculate_monthly_benefits
.. autofunction:: footings_idi_model.policy_models.dlr_stochastic.calculate_val_date_items
.. autofunction:: footings_idi_model.policy_models.dlr_stochastic.simulate_benefits
.. autofunction:: footings_idi_model.policy_models.dlr_stochastic.to_output_format

|

ALR Deterministic
-----------------

.. autofunction:: footings_idi_model.policy_models.alr_deterministic_model

|

.. autofunction:: footings_idi_model.functions.active_lives.create_alr_frame
.. autofunction:: footings_idi_model.functions.active_lives.calculate_lives
.. autofunction:: footings_idi_model.functions.active_lives.calculate_discount
.. autofunction:: footings_idi_model.functions.active_lives.calculate_incidence_rate
.. autofunction:: footings_idi_model.functions.active_lives.model_disabled_lives
.. autofunction:: footings_idi_model.functions.active_lives.calculate_claim_cost
.. autofunction:: footings_idi_model.functions.active_lives.calculate_pvfb
.. autofunction:: footings_idi_model.functions.active_lives.calculate_pvnfb
.. autofunction:: footings_idi_model.functions.active_lives.calculate_alr_from_issue
.. autofunction:: footings_idi_model.functions.active_lives.calculate_alr_from_valuation_date
.. autofunction:: footings_idi_model.functions.active_lives.to_output_format

|

ROP Deterministic
-----------------

.. autofunction:: footings_idi_model.policy_models.rop_deterministic_model

|

.. autofunction:: footings_idi_model.functions.active_lives.create_alr_frame
.. autofunction:: footings_idi_model.functions.active_lives.calculate_lives
.. autofunction:: footings_idi_model.functions.active_lives.calculate_discount
.. autofunction:: footings_idi_model.functions.active_lives.calculate_incidence_rate
.. autofunction:: footings_idi_model.functions.active_lives.model_disabled_lives
.. autofunction:: footings_idi_model.functions.active_lives.calculate_rop_payment_intervals
.. autofunction:: footings_idi_model.functions.active_lives.calculate_rop_future_disabled_claims
.. autofunction:: footings_idi_model.functions.active_lives.calculate_rop_expected_claim_payments
.. autofunction:: footings_idi_model.functions.active_lives.calculate_rop_benefits
.. autofunction:: footings_idi_model.functions.active_lives.calculate_pvfb
.. autofunction:: footings_idi_model.functions.active_lives.calculate_pvnfb
.. autofunction:: footings_idi_model.functions.active_lives.calculate_alr_from_issue
.. autofunction:: footings_idi_model.functions.active_lives.calculate_alr_from_valuation_date
.. autofunction:: footings_idi_model.functions.active_lives.to_output_format

|

Population Models
=================

|

Disabled Lives Model
--------------------

|

.. autofunction:: footings_idi_model.population_models.disabled_lives_model

|

.. autofunction:: footings_idi_model.population_models.disabled_lives.check_extract
.. autofunction:: footings_idi_model.population_models.disabled_lives.run_policy_model_per_record
.. autofunction:: footings_idi_model.population_models.disabled_lives.create_output

|

Active Lives Model
------------------

|

.. autofunction:: footings_idi_model.population_models.active_lives_model

|

.. autofunction:: footings_idi_model.population_models.active_lives.check_extracts
.. autofunction:: footings_idi_model.population_models.active_lives.run_policy_model_per_record
.. autofunction:: footings_idi_model.population_models.active_lives.create_output

|

Utilities
=========

|

Extract Generator
-----------------

|

.. autofunction:: footings_idi_model.utils.extract_generator_model

.. autofunction:: footings_idi_model.functions.generate_policies.create_frame
.. autofunction:: footings_idi_model.functions.generate_policies.sample_from_volume_tbl
.. autofunction:: footings_idi_model.functions.generate_policies.add_premium_and_benefits
.. autofunction:: footings_idi_model.functions.generate_policies.calculate_ages
.. autofunction:: footings_idi_model.functions.generate_policies.calculate_dates
.. autofunction:: footings_idi_model.functions.generate_policies.finalize_extract

