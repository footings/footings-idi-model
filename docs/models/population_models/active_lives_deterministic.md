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


# Active Lives Deterministic

## Documentation

```{eval-rst}
.. autoclass:: footings_idi_model.population_models.ActiveLivesDeterministicModel
```

## Usage

```{code-cell} ipython3
import pandas as pd
from footings_idi_model.population_models import ActiveLivesDeterministicModel
```

```{code-cell} ipython3
base_extract = pd.read_csv("active-lives-sample-base.csv")
base_extract

```{code-cell} ipython3
rider_extract = pd.read_csv(\"active-lives-sample-riders.csv\")"
rider_extract
```

```{code-cell} ipython3
model = ActiveLivesDeterministicModel(
    base_extract=base_extract,
    rider_extract=rider_extract,
    valuation_dt=pd.Timestamp("2020-03-31"),
    withdraw_table="01CSO",
    assumption_set="stat",
    net_benefit_method="NLP",
)
```

To run the model call the `run` method which returns -

- the projected reserve for each policy in the extract (`projected`),
- the reserve as of the valuation date for each policy (`time0`), and
- policies that error out when the model runs (`run`).

```{code-cell} ipython3
errors, projected, time0 = model.run()
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
model.audit("Audit-ActiveLivesDeterministicModel.xlsx")
```

The audit file can be downloaded {download}`here.<./Audit-ActiveLivesDeterministicModel.xlsx>`
