import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest
from requests import Request
from requests.exceptions import InvalidURL


@pytest.mark.parametrize("package", ["certifi", "soupsieve", "lxml", "pytest", "Pygments", "urllib3", "idna"])
def test_installed_dependency_matches_lockfile(package):
    lock = tomllib.loads((Path(__file__).resolve().parents[1] / "uv.lock").read_text())
    locked_version = next(p["version"] for p in lock["package"] if p["name"].lower() == package.lower())

    assert version(package) == locked_version


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://b\u00fccher.de/article", "https://xn--bcher-kva.de/article"),
        ("https://\u4f8b\u3048.\u30c6\u30b9\u30c8/article", "https://xn--r8jz45g.xn--zckzah/article"),
    ],
)
def test_unicode_and_punycode_urls_prepare_identically(url, expected):
    assert Request("GET", url).prepare().url == expected
    assert Request("GET", expected).prepare().url == expected


@pytest.mark.parametrize("url", ["https://\u200dexample.org/", "https://\u0308example.org/"])
def test_invalid_unicode_hostname_is_rejected(url):
    with pytest.raises(InvalidURL):
        Request("GET", url).prepare()
