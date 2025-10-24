import shutil
import subprocess
from pathlib import Path


def test_cli_generates_md_and_html_and_cleans_up():
    project_root = Path(__file__).resolve().parents[1]
    # Using uvx console script; no direct script path required

    # Work in a temporary subdirectory inside the project so `uv` finds pyproject.toml
    workdir = project_root / ".tmp_cli_integration"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "uvx",
        "--from",
        str(project_root),
        "grabit",
        "--no-create-domain-subdir",
        "-f",
        "md",
        "-f",
        "html",
        "https://example.com",
    ]

    expected_md = workdir / "Example Domain.md"
    expected_html = workdir / "Example Domain.html"

    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )

        if proc.returncode != 0:
            raise AssertionError(f"CLI exited with {proc.returncode}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        assert expected_md.exists(), "Expected Markdown file was not created"
        assert expected_html.exists(), "Expected HTML file was not created"
    finally:
        if workdir.exists():
            shutil.rmtree(workdir)
