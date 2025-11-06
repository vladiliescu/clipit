from __future__ import annotations

from bs4 import BeautifulSoup
from clipit.core.image_processor import extract_image_urls, process_images


def test_extract_image_urls_resolves_relative_and_deduplicates():
    html = """
    <html>
        <body>
            <img src="/images/photo.jpg">
            <img src="https://cdn.example.com/logo.png">
            <img src="/images/photo.jpg">
            <img src="data:image/png;base64,AAAA">
        </body>
    </html>
    """

    urls = extract_image_urls(html, "https://example.com/articles/123")

    assert urls == ["https://example.com/images/photo.jpg", "https://cdn.example.com/logo.png"]


def test_generate_image_filename_handles_duplicates_and_extensions(monkeypatch):
    """Verifies that:
    1. Original extension is preserved (image.PNG)
    2. Duplicate names get numbered (image_1.PNG)
    3. Missing extensions get default extension (.jpg added to banner)
    """
    html = """
    <html>
        <body>
            <img src="/assets/image.PNG">
            <img src="/assets/image.PNG?size=large">
            <img src="/assets/banner">
        </body>
    </html>
    """

    def fake_download(url: str, user_agent: str | None):
        return b"fake-image-data"

    monkeypatch.setattr("clipit.core.image_processor.download_image", fake_download)

    processed_html, images = process_images(html, "test-title", "https://example.com/page", user_agent=None)

    filenames = [filename for filename, _ in images]

    assert filenames == ["test-title/image.PNG", "test-title/image_1.PNG", "test-title/banner.jpg"]


def test_process_images_downloads_once_and_rewrites_src(monkeypatch):
    html = """
    <html>
        <body>
            <img src="/assets/photo.jpg">
            <img src="/assets/photo.jpg">
            <img src="https://cdn.example.com/logo">
        </body>
    </html>
    """

    download_calls: list[str] = []

    def fake_download(url: str, user_agent: str | None):
        download_calls.append(url)
        return f"bytes-for-{url}".encode()

    monkeypatch.setattr("clipit.core.image_processor.download_image", fake_download)

    processed_html, images = process_images(html, "test-title", "https://example.com/page", user_agent=None)

    soup = BeautifulSoup(processed_html, "html.parser")
    rewritten_sources = [img["src"] for img in soup.find_all("img")]

    assert download_calls == [
        "https://example.com/assets/photo.jpg",
        "https://cdn.example.com/logo",
    ]

    assert rewritten_sources == ["test-title/photo.jpg", "test-title/photo.jpg", "test-title/logo.jpg"]

    assert images == [
        ("test-title/photo.jpg", b"bytes-for-https://example.com/assets/photo.jpg"),
        ("test-title/logo.jpg", b"bytes-for-https://cdn.example.com/logo"),
    ]


def test_process_images_preserves_original_src_on_failure(monkeypatch):
    html = """
    <html>
        <body>
            <img src="/assets/photo.jpg">
            <img src="/assets/fallback.png">
        </body>
    </html>
    """

    def fake_download(url: str, user_agent: str | None):
        if url.endswith("photo.jpg"):
            return None
        return b"image-bytes"

    monkeypatch.setattr("clipit.core.image_processor.download_image", fake_download)

    processed_html, images = process_images(html, "test-title", "https://example.com/page", user_agent=None)
    soup = BeautifulSoup(processed_html, "html.parser")
    rewritten_sources = [img["src"] for img in soup.find_all("img")]

    assert rewritten_sources == ["/assets/photo.jpg", "test-title/fallback.png"]
    assert images == [("test-title/fallback.png", b"image-bytes")]
