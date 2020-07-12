
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

.. autofunction:: footings_idi_model.functions.dlr.create_dlr_frame
.. autofunction:: footings_idi_model.functions.dlr.calculate_ctr
.. autofunction:: footings_idi_model.functions.dlr.calculate_cola_adjustment
.. autofunction:: footings_idi_model.functions.dlr.calculate_monthly_benefits
.. autofunction:: footings_idi_model.functions.dlr.calculate_lives
.. autofunction:: footings_idi_model.functions.dlr.calculate_discount
.. autofunction:: footings_idi_model.functions.dlr.calculate_pvfb
.. autofunction:: footings_idi_model.functions.dlr.calculate_dlr
.. autofunction:: footings_idi_model.functions.dlr.to_output_format

|

ALR Deterministic
-----------------

.. autofunction:: footings_idi_model.policy_models.alr_deterministic_model

|

.. autofunction:: footings_idi_model.functions.alr.create_alr_frame
.. autofunction:: footings_idi_model.functions.alr.calculate_lives
.. autofunction:: footings_idi_model.functions.alr.calculate_discount
.. autofunction:: footings_idi_model.functions.alr.calculate_cola_adjustment
.. autofunction:: footings_idi_model.functions.alr.calculate_benefit_amount
.. autofunction:: footings_idi_model.functions.alr.calculate_incidence_rate
.. autofunction:: footings_idi_model.functions.alr.calculate_claim_cost
.. autofunction:: footings_idi_model.functions.alr.calculate_pvfb
.. autofunction:: footings_idi_model.functions.alr.calculate_pvnfb
.. autofunction:: footings_idi_model.functions.alr.calculate_alr_from_issue
.. autofunction:: footings_idi_model.functions.alr.calculate_alr_from_valuation_date
.. autofunction:: footings_idi_model.functions.alr.to_output_format

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

.. autofunction:: footings_idi_model.population_models.active_lives.check_extract
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
.. autofunction:: footings_idi_model.functions.generate_policies.add_benefit_amount
.. autofunction:: footings_idi_model.functions.generate_policies.calculate_ages
.. autofunction:: footings_idi_model.functions.generate_policies.calculate_dates
.. autofunction:: footings_idi_model.functions.generate_policies.finalize_extract

