from importlib.metadata import PackageNotFoundError, version

from grabit_md.core import GrabitError, OutputFormat
from grabit_md.grabber import Grabber

try:
    __version__ = version("grabit-md")
except PackageNotFoundError:
    # Fallback when running from source without installation
    __version__ = "dev"

__all__ = [
    "__version__",
    "Grabber",
    "OutputFormat",
    "GrabitError",
]
