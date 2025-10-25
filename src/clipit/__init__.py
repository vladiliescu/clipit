from importlib.metadata import PackageNotFoundError, version

from clipit.core import ClipitError, OutputFormat
from clipit.grabber import Grabber

try:
    __version__ = version("clipit")
except PackageNotFoundError:
    # Fallback when running from source without installation
    __version__ = "dev"

__all__ = [
    "__version__",
    "Grabber",
    "OutputFormat",
    "ClipitError",
]
