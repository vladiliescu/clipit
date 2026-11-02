from urllib.parse import unquote, urlparse

import pytest
import yaml
from bs4 import BeautifulSoup
from click.testing import CliRunner
from clipit import Clipper
from clipit.cli import main
from clipit.clipper import grabbers
from clipit.core import ClipitError, DownloadError, OutputFormat
from clipit.core.downloader import download_html_content
from clipit.core.misc import sanitize_filename
from clipit.grabbers import BaseGrabber, HuggingFaceGrabber
from markdown_it import MarkdownIt

MODEL_URL = "https://huggingface.co/NeuML/pubmedbert-base-embeddings"
DATASET_URL = "https://huggingface.co/datasets/qiaojin/PubMedQA"
MISSING_README_URL = "https://huggingface.co/hf-internal-testing/tiny-random-gpt2"


@pytest.fixture(scope="module", params=[MODEL_URL, DATASET_URL], ids=["model", "dataset"])
def repository(request):
    url = request.param
    title = urlparse(url).path.strip("/")
    raw_readme = download_html_content(f"{url}/raw/main/README.md", None)
    return url, title, raw_readme


@pytest.mark.parametrize(
    "url",
    [
        MODEL_URL,
        DATASET_URL,
        f"{MODEL_URL}/",
        f"{DATASET_URL}/",
        f"{MODEL_URL}?not-for-all-audiences=true#model-card",
        f"{DATASET_URL}?row=0#dataset-card",
        "http://huggingface.co/NeuML/pubmedbert-base-embeddings",
        "https://HUGGINGFACE.CO/owner/repo.name-with_underscores",
        "https://hf.co/NeuML/pubmedbert-base-embeddings",
        "https://hf.co/datasets/qiaojin/PubMedQA",
    ],
)
def test_huggingface_grabber_handles_repository_homepages(url):
    assert HuggingFaceGrabber().can_handle(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/NeuML/pubmedbert-base-embeddings",
        "https://huggingface.co.example.com/NeuML/pubmedbert-base-embeddings",
        "https://example.com@huggingface.co/NeuML/pubmedbert-base-embeddings",
        "https://huggingface.co",
        "https://huggingface.co/NeuML",
        "https://huggingface.co/gpt2",
        "https://huggingface.co/datasets",
        "https://huggingface.co/datasets/NeuML",
        f"{MODEL_URL}/tree/main",
        f"{DATASET_URL}/tree/main",
        f"{MODEL_URL}/blob/main/README.md",
        f"{DATASET_URL}/resolve/main/README.md",
        f"{MODEL_URL}/discussions",
        f"{DATASET_URL}/discussions",
        "https://huggingface.co/spaces/NeuML",
        "https://huggingface.co/spaces/NeuML/txtai",
        "https://huggingface.co/docs/hub",
        "https://huggingface.co/blog/embeddings",
        "https://huggingface.co/collections/NeuML",
        "https://huggingface.co/inference/models",
        "https://huggingface.co/join/discord",
        "https://huggingface.co/learn/nlp-course",
        "https://huggingface.co/api/models",
        "https://huggingface.co/organizations/NeuML",
        "https://huggingface.co/papers/trending",
        "https://huggingface.co/search/full-text",
        "https://huggingface.co/settings/profile",
        "https://huggingface.co/oauth/authorize",
        "https://huggingface.co/models/bert",
        "https://huggingface.co/tasks/sentence-similarity",
        "ftp://huggingface.co/NeuML/pubmedbert-base-embeddings",
    ],
)
def test_huggingface_grabber_leaves_other_urls_to_existing_grabbers(url):
    assert not HuggingFaceGrabber().can_handle(url)


@pytest.mark.parametrize("url", [MODEL_URL, DATASET_URL])
def test_huggingface_grabber_owns_readme_preference(url):
    grabber = HuggingFaceGrabber()

    assert not grabber.can_handle(url, use_readme=False)
    assert grabber.can_handle(url, use_readme=True)
    assert grabber.can_handle(url)


@pytest.mark.parametrize("url", [MODEL_URL, DATASET_URL])
@pytest.mark.parametrize("use_readme, expected_type", [(True, HuggingFaceGrabber), (False, BaseGrabber)])
def test_readme_preference_selects_huggingface_or_webpage_grabber(url, use_readme, expected_type):
    grabber = next(g for g in grabbers if g.can_handle(url, use_readme=use_readme))

    assert type(grabber) is expected_type


@pytest.mark.parametrize("formats", [["md"], ["stdout.md"], ["md", "stdout.md"]])
def test_readme_outputs_preserve_raw_content_and_requested_formats(repository, formats):
    url, expected_title, raw_readme = repository
    title, outputs, images = Clipper().clip(
        url=f"{url}/",
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=formats,
    )

    assert title == expected_title
    assert set(outputs) == {OutputFormat(fmt) for fmt in formats}
    assert all(content == raw_readme for content in outputs.values())
    assert images == []


def test_stdout_only_keeps_raw_readme_without_downloading_images(repository):
    url, _, raw_readme = repository
    _, outputs, images = Clipper().clip(
        url=url,
        use_readability_js=True,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["stdout.md"],
        download_images=True,
    )

    assert outputs == {OutputFormat.STDOUT_MD: raw_readme}
    assert images == []


def test_readme_metadata_and_saving_preserve_repository_source(repository, tmp_path, monkeypatch):
    url, title, raw_readme = repository
    monkeypatch.chdir(tmp_path)
    source_url = f"{url}?source=bookmark#card"
    Clipper().clip_and_save(
        url=source_url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=True,
        include_title=True,
        yaml_frontmatter=True,
        output_formats=["md"],
        create_domain_subdir=True,
        overwrite=False,
    )

    markdown = (tmp_path / "huggingface.co" / f"{sanitize_filename(title)}.md").read_text()
    metadata = yaml.safe_load(markdown.split("---", 2)[1])
    assert metadata["title"] == title
    assert metadata["source"] == source_url
    assert f"# {title}\n\n" in markdown
    assert f"[Source]({source_url})\n\n" in markdown
    assert markdown.endswith(raw_readme)


@pytest.mark.parametrize(
    "formats",
    [["md", "html"], ["stdout.md", "raw.html"], ["md", "stdout.md", "html", "raw.html"]],
)
def test_mixed_outputs_use_raw_readme_and_webpage_html(repository, formats):
    url, _, raw_readme = repository
    _, outputs, images = Clipper().clip(
        url=url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=formats,
    )

    assert set(outputs) == {OutputFormat(fmt) for fmt in formats}
    for fmt in (OutputFormat.MD, OutputFormat.STDOUT_MD):
        if fmt in outputs:
            assert outputs[fmt] == raw_readme
    if OutputFormat.READABLE_HTML in outputs:
        assert BeautifulSoup(outputs[OutputFormat.READABLE_HTML], "html.parser").get_text(strip=True)
    if OutputFormat.RAW_HTML in outputs:
        page = BeautifulSoup(outputs[OutputFormat.RAW_HTML], "html.parser")
        assert page.title is not None
        assert "Hugging Face" in page.title.get_text()
    assert images == []


@pytest.mark.parametrize("formats", [["md"], ["md", "html"]])
def test_image_mode_preserves_metadata_without_adding_unrequested_formats(repository, formats):
    url, _, raw_readme = repository
    _, outputs, _ = Clipper().clip(
        url=url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=formats,
        download_images=True,
    )

    assert set(outputs) == {OutputFormat(fmt) for fmt in formats}
    assert yaml.safe_load(outputs[OutputFormat.MD].split("---", 2)[1]) == yaml.safe_load(raw_readme.split("---", 2)[1])


def test_html_only_keeps_webpage_extraction_without_readme_warning(caplog):
    _, outputs, _ = Clipper().clip(
        url=MISSING_README_URL,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["html", "raw.html"],
    )

    assert set(outputs) == {OutputFormat.READABLE_HTML, OutputFormat.RAW_HTML}
    assert outputs[OutputFormat.READABLE_HTML]
    assert "No README found" not in caplog.text


def test_missing_readme_falls_back_to_webpage_with_warning(caplog):
    title, outputs, images = Clipper().clip(
        url=MISSING_README_URL,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["stdout.md"],
    )

    assert title
    assert outputs[OutputFormat.STDOUT_MD]
    assert images == []
    assert f"No README found for {MISSING_README_URL}; falling back to webpage extraction." in caplog.text


def test_cli_defaults_to_readme_and_can_opt_out(repository):
    url, _, raw_readme = repository
    args = [url, "--no-use-readability-js", "--no-yaml-frontmatter", "--no-include-title", "-f", "stdout.md"]
    readme_result = CliRunner().invoke(main, args)
    webpage_result = CliRunner().invoke(main, [*args, "--no-use-readme"])

    assert readme_result.exit_code == 0, readme_result.output
    assert readme_result.stdout == f"{raw_readme}\n"
    assert webpage_result.exit_code == 0, webpage_result.output
    assert webpage_result.stdout
    assert webpage_result.stdout != readme_result.stdout


def test_library_can_opt_out_of_readme_when_saving(repository, tmp_path, monkeypatch):
    url, _, raw_readme = repository
    monkeypatch.chdir(tmp_path)
    Clipper().clip_and_save(
        url=url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["md"],
        create_domain_subdir=False,
        overwrite=False,
        use_readme=False,
    )

    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert files[0].read_text()
    assert files[0].read_text() != raw_readme


def test_unavailable_repository_does_not_silently_fall_back(caplog):
    url = "https://huggingface.co/hf-internal-testing/clipit-repository-that-does-not-exist"
    with pytest.raises(DownloadError):
        HuggingFaceGrabber()._get_readme(url, None)

    assert "No README found" not in caplog.text


def test_download_failure_keeps_cli_bookmark_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = "https://huggingface.co/hf-internal-testing/clipit-repository-that-does-not-exist"
    result = CliRunner().invoke(
        main,
        [url, "--bookmark-on-failure", "--title", "Model", "--notes", "Read later.", "-f", "stdout.md"],
    )

    assert result.exit_code == 0, result.output
    metadata = yaml.safe_load(result.stdout.split("---", 2)[1])
    assert metadata["source"] == url
    assert metadata["title"] == "Model"
    assert "Read later." in result.stdout
    assert "401" in result.stderr
    assert not list(tmp_path.iterdir())


def test_missing_rendered_card_raises_an_extraction_error():
    homepage = download_html_content("https://huggingface.co", None)
    with pytest.raises(ClipitError, match="No rendered Hugging Face README found"):
        HuggingFaceGrabber()._get_readme_html(MODEL_URL, None, homepage)


@pytest.mark.parametrize(
    "url",
    [
        "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5",
        "https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu",
    ],
    ids=["model", "dataset"],
)
def test_readme_and_webpage_images_preserve_hub_metadata_and_valid_links(url, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_readme = download_html_content(f"{url}/raw/main/README.md", None)
    title = urlparse(url).path.strip("/")
    Clipper().clip_and_save(
        url=url,
        use_readability_js=True,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["md", "html", "raw.html"],
        create_domain_subdir=True,
        overwrite=False,
        download_images=True,
        download_folder="attachments/${domain}/${file_name}",
    )

    output_dir = tmp_path / "huggingface.co"
    file_name = sanitize_filename(title)
    markdown = (output_dir / f"{file_name}.md").read_text()
    readable_html = BeautifulSoup((output_dir / f"{file_name}.html").read_text(), "html.parser")
    raw_html = BeautifulSoup((output_dir / f"{file_name}.raw.html").read_text(), "html.parser")
    card = raw_html.select_one("main .prose")
    assert card is not None
    assert card.select("img")
    assert yaml.safe_load(markdown.split("---", 2)[1]) == yaml.safe_load(raw_readme.split("---", 2)[1])
    assert "../attachments/huggingface.co/" in markdown
    image_paths = list((tmp_path / "attachments" / "huggingface.co" / file_name).iterdir())
    assert image_paths
    assert all(path.read_bytes() for path in image_paths)
    markdown_images = [
        child.attrGet("src")
        for token in MarkdownIt().enable("table").parse(markdown)
        for child in token.children or []
        if child.type == "image"
    ]
    assert len(markdown_images) == len(card.select("img"))
    for src in markdown_images:
        assert isinstance(src, str)
        assert (output_dir / unquote(src)).resolve() in image_paths
    for image in readable_html.select("img"):
        src = str(image["src"])
        if not urlparse(src).scheme:
            assert (output_dir / unquote(src)).resolve() in image_paths
    assert all(urlparse(str(image["src"])).scheme for image in card.select("img"))
