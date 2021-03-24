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

# Extracts

## Active Lives - Base

```{eval-rst}
.. autodata:: footings_idi_model.extracts.ActiveLivesBaseExtract
   :no-value:
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
extract_base = pd.read_csv(
  "./models/extract_models/active-lives-sample-base.csv",
  parse_dates=["BIRTH_DT", "POLICY_START_DT", "PREMIUM_PAY_TO_DT", "POLICY_END_DT"]
)
extract_base
```

## Active Lives - ROP Rider

```{eval-rst}
.. autodata:: footings_idi_model.extracts.ActiveLivesROPRiderExtract
   :no-value:
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
extract_riders = pd.read_csv(
  "./models/extract_models/active-lives-sample-riders-rop.csv",
)
extract_riders
```

## Disabled Lives - Base

```{eval-rst}
.. autodata:: footings_idi_model.extracts.DisabledLivesBaseExtract
   :no-value:
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
extract_base = pd.read_csv(
  "./models/extract_models/disabled-lives-sample-base.csv",
  parse_dates=["BIRTH_DT", "INCURRED_DT", "TERMINATION_DT"]
)
extract_base
```

## Disabled Lives - Rider

```{eval-rst}
.. autodata:: footings_idi_model.extracts.DisabledLivesRiderExtract
   :no-value:
```

### Sample Data

```{code-cell} ipython3
---
tags: [hide-input]
---
import pandas as pd
extract_riders = pd.read_csv(
  "./models/extract_models/disabled-lives-sample-riders.csv",
)
extract_riders
```
