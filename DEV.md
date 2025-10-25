```sh

# Install the project in editable mode
uv pip install -e .

# Run tests
uv run pytest

# Run app in dev-mode

# Using uvx console script (local project)
uvx --from . clipit --help

uvx --from . clipit [OPTIONS] URL

# Legacy shim (still works during migration)
uv run python clipit.py --help

uv run python clipit.py [OPTIONS] URL

```
