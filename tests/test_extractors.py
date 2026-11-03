import shutil
from pathlib import Path

import pytest
import yaml
from clipit import Clipper
from clipit.core import OutputFormat, extractor
from clipit.core.readabilipy_runtime import ensure_readabilipy_node_runtime


@pytest.mark.parametrize("page", ["example-domain", "boring-table"])
@pytest.mark.parametrize("use_javascript", [False, True], ids=["python", "javascript"])
def test_saved_pages_preserve_real_extraction_outputs(page_server, saved_page_expectations, page, use_javascript):
    if use_javascript:
        if shutil.which("node") is None or shutil.which("npm") is None:
            pytest.skip("Node.js and npm are required for JavaScript extraction")
        assert ensure_readabilipy_node_runtime(), "The installed JavaScript runtime must work, not silently fall back"

    fixtures = Path(__file__).parent / "fixtures"
    expected = saved_page_expectations[page]["javascript" if use_javascript else "python"]
    title, outputs, images = Clipper().clip(
        url=f"{page_server}/{page}.html",
        use_readability_js=use_javascript,
        fallback_title="Saved page",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["md", "stdout.md", "html", "raw.html"],
    )

    assert title == expected["title"]
    assert {fmt.value: content for fmt, content in outputs.items()} == {
        "md": expected["md"],
        "stdout.md": expected["md"],
        "html": expected["html"],
        "raw.html": (fixtures / f"{page}.html").read_text(),
    }
    assert images == []


def test_saved_page_preserves_markdown_metadata(page_server, saved_page_expectations):
    url = f"{page_server}/example-domain.html"
    title, outputs, _ = Clipper().clip(
        url=url,
        use_readability_js=False,
        fallback_title="Saved page",
        include_source=True,
        include_title=True,
        yaml_frontmatter=True,
        output_formats=["md"],
    )

    metadata_text, body = outputs[OutputFormat.MD].split("---", 2)[1:]
    metadata = yaml.safe_load(metadata_text)
    expected = saved_page_expectations["example-domain"]["python"]
    assert metadata["title"] == title == expected["title"]
    assert metadata["source"] == url
    assert set(metadata) == {"title", "source", "date"}
    assert body == f"\n\n# {title}\n\n[Source]({url})\n\n{expected['md']}"


def test_extract_readable_content_uses_python_mode_when_runtime_is_unavailable(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: False)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"


def test_extract_readable_content_falls_back_to_python_mode_when_js_extracts_no_content(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        if use_readability:
            return {"content": "", "title": "Example"}
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: True)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [True, False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"


def test_extract_readable_content_falls_back_to_python_mode_when_js_raises(monkeypatch):
    observed_calls: list[bool] = []

    def fake_simple_json_from_html_string(_html_content, use_readability):
        observed_calls.append(use_readability)
        if use_readability:
            raise RuntimeError("broken js runtime")
        return {"content": "<p>Example</p>", "title": "Example"}

    monkeypatch.setattr(extractor, "ensure_readabilipy_node_runtime", lambda: True)
    monkeypatch.setattr(extractor, "simple_json_from_html_string", fake_simple_json_from_html_string)

    content_html, title = extractor.extract_readable_content_and_title("<html></html>", True)

    assert observed_calls == [True, False]
    assert content_html == "<p>Example</p>"
    assert title == "Example"
