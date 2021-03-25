---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Footings IDI Model
  language: python
  name: footings-idi-model

execution:
  timeout: -1
---


# Active Lives - Deterministic

## Valuation Model
### Documentation

```{eval-rst}
.. autoclass:: footings_idi_model.models.ActiveLivesValEMD
```

### Usage

```{code-cell} ipython3
import pandas as pd
from footings_idi_model.models import ActiveLivesValEMD
```

```{code-cell} ipython3
extract_base = pd.read_csv(
  "active-lives-sample-base.csv",
  parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"]
)
extract_base
```

```{code-cell} ipython3
extract_riders = pd.read_csv("active-lives-sample-riders.csv")
extract_riders
```

```{code-cell} ipython3
model = ActiveLivesValEMD(
    extract_base=extract_base,
    extract_riders=extract_riders,
    valuation_dt=pd.Timestamp("2020-03-31"),
    assumption_set="STAT",
    net_benefit_method="NLP",
)
```

To run the model call the `run` method which returns -

- the projected reserve for each policy in the extract (`projected`),
- the reserve as of the valuation date for each policy (`time0`), and
- policies that error out when the model runs (`run`).

```{code-cell} ipython3
projected, time0, errors = model.run()
```

Note the `time0` and `projected` have the same columns with `time0` being a subset of the `projected` frame.

```{code-cell} ipython3
projected.info()
```

```{code-cell} ipython3
projected
```

```{code-cell} ipython3
time0
```

```{code-cell} ipython3
errors
```

An audit of the model is ran by calling the `audit` method as shown below.

```{code-cell} ipython3
model.audit("Audit-ActiveLivesValEMD.xlsx")
```

The audit file can be downloaded {download}`here.<./Audit-ActiveLivesValEMD.xlsx>`

## Projection Model

### Documentation

To be completed.

### Usage

To be completed.
