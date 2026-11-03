from pathlib import Path

import pytest
from clipit import Clipper, clipper
from clipit.core import OutputFormat
from clipit.grabbers import BaseGrabber


class LegacyGrabber(BaseGrabber):
    def can_handle(self, url: str) -> bool:
        return url.endswith("/article.html")


@pytest.mark.parametrize("use_readme", [True, False])
def test_request_eligibility_preserves_legacy_url_matching(use_readme):
    grabber = LegacyGrabber()

    assert grabber.can_handle_request("https://example.com/article.html", use_readme=use_readme)
    assert not grabber.can_handle_request("https://example.com/other.html", use_readme=use_readme)


@pytest.mark.parametrize("use_readme", [True, False])
def test_clipper_supports_registered_grabber_with_url_only_signature(image_server, monkeypatch, use_readme):
    base_url, directory, received_requests = image_server
    article = (Path(__file__).parent / "fixtures" / "boring-table.html").read_text()
    (directory / "article.html").write_text(
        f"<html><head><title>Choose Boring Technology</title></head><body>{article}</body></html>"
    )
    monkeypatch.setattr(clipper, "grabbers", [LegacyGrabber()])

    title, outputs, images = Clipper().clip(
        url=f"{base_url}/article.html",
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["stdout.md"],
        use_readme=use_readme,
    )

    assert title == "Choose Boring Technology"
    assert set(outputs) == {OutputFormat.STDOUT_MD}
    assert "Dan McKinley" in outputs[OutputFormat.STDOUT_MD]
    assert images == []
    assert received_requests == ["/article.html"]


@pytest.mark.parametrize("use_readme", [True, False])
def test_clipper_respects_legacy_grabber_declining_url(monkeypatch, use_readme):
    monkeypatch.setattr(clipper, "grabbers", [LegacyGrabber()])

    with pytest.raises(ValueError, match="No grabber found"):
        Clipper().clip(
            url="https://example.com/other.html",
            use_readability_js=False,
            fallback_title="Untitled {date}",
            include_source=False,
            include_title=False,
            yaml_frontmatter=False,
            output_formats=["stdout.md"],
            use_readme=use_readme,
        )
