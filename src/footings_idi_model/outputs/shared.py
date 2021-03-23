from footings.data_dictionary import def_column

MODEL_VERSION = def_column(dtype="string", description="The tagged model version.")
LAST_COMMIT = def_column(dtype="string", description="The last git commit.")
RUN_DATE_TIME = def_column(dtype="datetime64[ns]", description="The run date and time.")
SOURCE = def_column(dtype="string", description="The underlying policy model used.")
