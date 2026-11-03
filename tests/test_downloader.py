from pathlib import Path

import pytest
from clipit.core import DownloadError
from clipit.core.downloader import download_html_content
from requests.exceptions import SSLError


@pytest.mark.parametrize("path", ["example-domain.html", "redirect", "compressed"])
def test_download_preserves_page_through_redirects_and_compression(page_server, path):
    expected = (Path(__file__).parent / "fixtures" / "example-domain.html").read_text()

    assert download_html_content(f"{page_server}/{path}", None) == expected


def test_download_reports_http_error(page_server):
    with pytest.raises(DownloadError, match="404"):
        download_html_content(f"{page_server}/missing", None)


def test_download_honors_no_proxy(page_server, monkeypatch):
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(name, "127.0.0.1")

    expected = (Path(__file__).parent / "fixtures" / "example-domain.html").read_text()
    assert download_html_content(f"{page_server}/example-domain.html", None) == expected


def test_download_rejects_untrusted_certificate(untrusted_https_server, monkeypatch):
    for name in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        monkeypatch.delenv(name, raising=False)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(name, "127.0.0.1")

    with pytest.raises(DownloadError) as error:
        download_html_content(untrusted_https_server, None)

    assert isinstance(error.value.__cause__, SSLError)
