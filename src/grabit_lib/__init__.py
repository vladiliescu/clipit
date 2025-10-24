from importlib.metadata import PackageNotFoundError, version

from grabit_lib.core import GrabitError, OutputFormat
from grabit_lib.grabber import Grabber

try:
    __version__ = version("grabit_lib")
except PackageNotFoundError:
    # Fallback when running from source without installation
    __version__ = "dev"

__all__ = [
    "__version__",
    "Grabber",
    "OutputFormat",
    "GrabitError",
]
