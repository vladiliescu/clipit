```sh

# Install the project in editable mode with all dependencies
uv sync

# Run tests
uv run pytest

# Run app in dev-mode (recommended - uses editable install, no cache issues)
uv run clipit --help
uv run clipit [OPTIONS] URL

# Alternative: Using uvx (requires cache clearing after code changes)
uvx --from . clipit --help
uvx --from . clipit [OPTIONS] URL


```
