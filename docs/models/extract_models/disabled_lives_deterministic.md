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


# Disabled Lives - Deterministic

## Valuation Model
### Documentation

```{eval-rst}
.. autoclass:: footings_idi_model.extract_models.DisabledLivesValEMD
```

### Usage

```{code-cell} ipython3
import pandas as pd
from footings_idi_model.extract_models import DisabledLivesValEMD
```

```{code-cell} ipython3
base_extract = pd.read_csv(
  "disabled-lives-sample.csv",
  parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"]
)
base_extract
```

```{code-cell} ipython3
model = DisabledLivesValEMD(
    base_extract=base_extract,
    rider_extract=pd.DataFrame(),
    valuation_dt=pd.Timestamp("2020-01-01"),
    assumption_set="stat",
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
model.audit("Audit-DisabledLivesValEMD.xlsx")
```

The audit file can be downloaded {download}`here.<./Audit-DisabledLivesValEMD.xlsx>`

## Projection Model

### Documentation

To be completed.

### Usage

To be completed.
