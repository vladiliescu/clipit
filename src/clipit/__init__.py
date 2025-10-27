from importlib.metadata import PackageNotFoundError, version

from clipit.clipper import Clipper
from clipit.core import ClipitError, OutputFormat

try:
    __version__ = version("clipit")
except PackageNotFoundError:
    # Fallback when running from source without installation
    __version__ = "dev"

__all__ = [
    "__version__",
    "Clipper",
    "OutputFormat",
    "ClipitError",
]
