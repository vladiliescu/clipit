# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.1.0,<8.2",
#   "grabit-md>=1.0.0",
# ]
# ///
from grabit_md.cli import main

if __name__ == "__main__":
    print("Running this script directly is deprecated, please use `uvx grabit [OPTIONS] url`")
    main()
