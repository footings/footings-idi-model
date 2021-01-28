from ._version import get_versions
from . import (
    data,
    assumptions,
    policy_models,
    extract_models,
)

versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
