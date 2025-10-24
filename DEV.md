```sh

# Install the project in editable mode
uv pip install -e .

# Run tests
uv run pytest

# Run app in dev-mode

# Using uvx console script (local project)
uvx --from . grabit --help

uvx --from . grabit [OPTIONS] URL

# Legacy shim (still works during migration)
uv run python grabit.py --help

uv run python grabit.py [OPTIONS] URL

```
