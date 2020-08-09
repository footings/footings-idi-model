import os

import pandas as pd
import yaml

directory, filename = os.path.split(__file__)

with open(os.path.join(directory, "extract-disabled-lives.yaml")) as file:
    disabled_life_schema = yaml.safe_load(file)
disabled_life_columns = pd.DataFrame.from_dict(disabled_life_schema["columns"])["name"]

with open(os.path.join(directory, "extract-active-lives-base.yaml")) as file:
    active_lives_base_schema = yaml.safe_load(file)
active_lives_base_columns = pd.DataFrame.from_dict(active_lives_base_schema["columns"])[
    "name"
]

with open(os.path.join(directory, "extract-active-lives-riders.yaml")) as file:
    active_lives_rider_schema = yaml.safe_load(file)
active_lives_rider_columns = pd.DataFrame.from_dict(active_lives_rider_schema["columns"])[
    "name"
]
