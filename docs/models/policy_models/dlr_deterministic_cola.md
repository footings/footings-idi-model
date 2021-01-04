---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3

execution:
  timeout: -1
---


# Disabled - Deterministic - COLA Rider

## Valuation Model

### Documentation

```{eval-rst}
.. autoclass:: footings_idi_model.policy_models.DValColaRPM
```

### Usage

```{code-cell} ipython3
import pandas as pd
from footings_idi_model.policy_models import DValColaRPM

model = DValColaRPM(
    policy_id="policy-1",
    claim_id="claim-1",
    gender="M",
    birth_dt=pd.Timestamp("1970-03-26"),
    incurred_dt=pd.Timestamp("2015-06-02"),
    termination_dt=pd.Timestamp("2035-03-26"),
    elimination_period=90,
    idi_contract="AS",
    idi_benefit_period="TO65",
    idi_diagnosis_grp="LOW",
    idi_occupation_class="M",
    cola_percent=0.02,
    benefit_amount=200.0,
    valuation_dt=pd.Timestamp("2020-03-31"),
    assumption_set="stat",
)
```

To run the model call the `run` method.

```{code-cell} ipython3
output = model.run()
```

The model returns a DataFrame of the projected reserves.

```{code-cell} ipython3
output.info()
```

```{code-cell} ipython3
output
```

An audit of the model is ran by calling the `audit` method shown below.

```{code-cell} ipython3
model.audit("Audit-DValColaRPM.xlsx")
```

The audit file can be downloaded {download}`here.<./Audit-DValColaRPM.xlsx>`


## Projection Model

### Documentation

To be completed.

### Usage

To be completed.
