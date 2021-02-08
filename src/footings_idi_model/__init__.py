from . import assumptions, data, extract_models, policy_models
from ._version import get_versions

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__version__ = importlib_metadata.version(__name__)
