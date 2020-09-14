import os

import pandas as pd
import yaml

directory, filename = os.path.split(__file__)


def get_categories(df, name):
    l = df[df["name"] == name]["allowed"].explode().to_list()
    return [str(x) for x in l]


def _schema_to_dict(schema):
    record = {}
    for column in schema.get("columns"):
        record.update(
            {column.get("name").lower(): {k: v for k, v in column.items() if k != "name"}}
        )
    return record


#########################################################################################
# disabled lives
#########################################################################################


with open(os.path.join(directory, "extract-disabled-lives.yaml")) as file:
    disabled_life_schema = yaml.safe_load(file)

disabled_base_schema = _schema_to_dict(disabled_life_schema)
df_disabled_life = pd.DataFrame.from_dict(disabled_life_schema["columns"])
disabled_life_columns = df_disabled_life["name"]

CAT_DIS_GENDER = get_categories(df_disabled_life, "GENDER")
CAT_DIS_IDI_OCCUPATION = get_categories(df_disabled_life, "IDI_OCCUPATION_CLASS")
CAT_DIS_IDI_CONTRACT = get_categories(df_disabled_life, "IDI_CONTRACT")
CAT_DIS_IDI_BENEFIT_PERIOD = get_categories(df_disabled_life, "IDI_BENEFIT_PERIOD")
CAT_DIS_IDI_MARKET = get_categories(df_disabled_life, "IDI_MARKET")
CAT_DIS_IDI_DIAGNOSIS_GRP = get_categories(df_disabled_life, "IDI_DIAGNOSIS_GRP")


#########################################################################################
# disabled lives
#########################################################################################


with open(os.path.join(directory, "extract-active-lives-base.yaml")) as file:
    active_lives_base_schema = yaml.safe_load(file)

active_base_schema = _schema_to_dict(active_lives_base_schema)
active_lives_base_columns = pd.DataFrame.from_dict(active_lives_base_schema["columns"])[
    "name"
]

with open(os.path.join(directory, "extract-active-lives-riders.yaml")) as file:
    active_lives_rider_schema = yaml.safe_load(file)

active_rider_schema = _schema_to_dict(active_lives_rider_schema)
active_lives_rider_columns = pd.DataFrame.from_dict(active_lives_rider_schema["columns"])[
    "name"
]
