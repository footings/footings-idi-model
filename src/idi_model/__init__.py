from .population_models import (
    disabled_lives_model,
    active_lives_model,
    extract_generator_model,
)

from ._version import get_versions

versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
