
==================
Footings IDI Model
==================

Summary
-------

This is a python library representing an actuarial model for individual disablity income insurance.
It was built using the `Footings <https://github.com/footings/footings>`_ modeling framework. There
are many benefits to using the footings framework which are listed on the Footings github site.

Features
--------

- Built-in 2013 individual disability income valuation tables
- Placeholder modes to run STAT, GAAP or best estimate assumptions.
- Ability to model both disabled life reserves (DLRs) and active life reserves (ALRs).
- Placeholders to model both deterministic reserves as well as stochastic reserves.

Installation
------------

To install the latest version on github run - ::

   pip install git+https://github.com/foootings/footings-idi-model.git

Resources
---------

Below are resources that were used to develop the model -

- `Footings documentation <https://footings.readthedocs.io/en/latest/>`_
- `American Academy of Actuaries 2013 IDI Valuation Table excel prototype <https://www.actuary.org/content/2013-idi-valuation-table-workbook-version-13>`_
- `Soceity of Actuaries (SOA) 2013 Individual Disablity Income Valuation Table <https://www.soa.org/resources/experience-studies/2016/hlth-2013-individual-disability-supporting-materials/>`_
- `Soceity of Actuaries (SOA) 2013 Individual Disability Insurance Valuation Table and Supporting Materials <https://www.soa.org/resources/experience-studies/2017/credit-disability-income/>`_

License
-------

BSD 3-Clause License

Copyright (c) 2020-2021, Dustin Tindall
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

.. toctree::
   :maxdepth: 2
   :hidden:

   product_info.rst
   user_guide.md
   extracts.md
   models/index.rst
   assumptions.md
   outputs.md
   scenarios.md
   changelog.md
