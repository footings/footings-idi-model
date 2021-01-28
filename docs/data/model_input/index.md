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

# Model Input (Extracts)

## Active Lives - Base

```{eval-rst}
.. autodata:: footings_idi_model.data.ActiveLivesBaseExtract
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
base_extract = pd.read_csv(
  "../../models/extract_models/active-lives-sample-base.csv",
  parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"]
)
base_extract
```

## Active Lives - Rider

```{eval-rst}
.. autodata:: footings_idi_model.data.ActiveLivesRiderExtract
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
rider_extract = pd.read_csv(
  "../../models/extract_models/active-lives-sample-riders.csv",
)
rider_extract
```

## Disabled Lives - Base

```{eval-rst}
.. autodata:: footings_idi_model.data.DisabledLivesBaseExtract
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
base_extract = pd.read_csv(
  "../../models/extract_models/disabled-lives-sample.csv",
  parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"]
)
base_extract
```

## Disabled Lives - Rider

```{eval-rst}
.. autodata:: footings_idi_model.data.DisabledLivesRiderExtract
```
