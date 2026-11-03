from urllib.parse import unquote, urlparse

import pytest
import yaml
from bs4 import BeautifulSoup
from click.testing import CliRunner
from clipit import Clipper
from clipit.cli import main
from clipit.clipper import grabbers
from clipit.core import OutputFormat
from clipit.core.downloader import download_html_content
from clipit.core.misc import sanitize_filename
from clipit.grabbers import BaseGrabber, GitHubGrabber, RedditGrabber
from markdown_it import MarkdownIt

HELLO_WORLD_URL = "https://github.com/octocat/Hello-World"
CLIPIT_URL = "https://github.com/vladiliescu/clipit"


@pytest.mark.parametrize(
    "url",
    [
        HELLO_WORLD_URL,
        f"{HELLO_WORLD_URL}/",
        f"{HELLO_WORLD_URL}.git",
        f"{HELLO_WORLD_URL}?tab=readme-ov-file#readme",
        "http://www.github.com/octocat/Hello-World",
        "https://GITHUB.COM/owner/repo.name-with_underscores",
    ],
)
def test_github_grabber_handles_repository_homepages(url):
    assert GitHubGrabber().can_handle(url)


def test_github_grabber_declines_when_readme_is_disabled():
    grabber = GitHubGrabber()

    assert not grabber.can_handle_request(HELLO_WORLD_URL, use_readme=False)
    assert grabber.can_handle_request(HELLO_WORLD_URL, use_readme=True)
    assert grabber.can_handle_request(HELLO_WORLD_URL)
    assert grabber.can_handle(HELLO_WORLD_URL)


@pytest.mark.parametrize("use_readme, expected_type", [(True, GitHubGrabber), (False, BaseGrabber)])
def test_readme_preference_selects_the_applicable_grabber(use_readme, expected_type):
    grabber = next(g for g in grabbers if g.can_handle_request(HELLO_WORLD_URL, use_readme=use_readme))

    assert type(grabber) is expected_type


@pytest.mark.parametrize("use_readme", [True, False])
def test_readme_preference_does_not_change_other_grabbers(use_readme):
    assert BaseGrabber().can_handle_request(HELLO_WORLD_URL, use_readme=use_readme)
    assert RedditGrabber().can_handle_request("https://www.reddit.com/r/python/", use_readme=use_readme)
    assert RedditGrabber().can_handle_request("https://old.reddit.com/r/python/", use_readme=use_readme)
    assert not RedditGrabber().can_handle_request(HELLO_WORLD_URL, use_readme=use_readme)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/octocat/Hello-World",
        "https://github.com.example.com/octocat/Hello-World",
        "https://example.com@github.com/octocat/Hello-World",
        "https://github.com",
        "https://github.com/octocat",
        f"{HELLO_WORLD_URL}/issues",
        f"{HELLO_WORLD_URL}/tree/master",
        f"{HELLO_WORLD_URL}/blob/master/README",
        "https://github.com/topics/python",
        "https://github.com/orgs/github",
        "https://github.com/sponsors/octocat",
        "https://github.com/trending/python",
        "https://github.com/trending/developers",
        "https://github.com/search/advanced",
        "https://github.com/login/device",
        "https://github.com/pulls/assigned",
        "https://github.com/new/import",
        "https://github.com/codespaces/new",
        "https://github.com/issues/assigned",
        "https://github.com/notifications/participating",
        "https://github.com/organizations/new",
        "https://github.com/readme/guides",
        "https://github.com/solutions/use-case",
        "https://github.com/resources/articles",
        "https://github.com/contact/report-abuse",
        "https://github.com/account/upgrade",
        "https://github.com/customer-stories/figma",
        "https://github.com/open-source/sponsors",
        "https://github.com/education/students",
        "https://github.com/pricing/calculator",
        "https://github.com/join/plan",
        "https://raw.githubusercontent.com/octocat/Hello-World/master/README",
        "ftp://github.com/octocat/Hello-World",
        "https://github.com/owner/repo/extra/",
    ],
)
def test_github_grabber_leaves_other_urls_to_existing_grabbers(url):
    assert not GitHubGrabber().can_handle(url)


@pytest.mark.parametrize("formats", [["md"], ["stdout.md"], ["md", "stdout.md"]])
def test_readme_outputs_match_requested_formats_and_use_default_branch(formats):
    title, outputs, images = Clipper().clip(
        url=f"{HELLO_WORLD_URL}/",
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=formats,
    )

    assert title == "octocat/Hello-World"
    assert set(outputs) == {OutputFormat(fmt) for fmt in formats}
    # This repository's default branch is master and its README has no file extension.
    assert all(content == "Hello World!\n" for content in outputs.values())
    assert images == []


def test_readme_body_is_preserved_without_html_conversion():
    raw_readme = download_html_content("https://raw.githubusercontent.com/vladiliescu/clipit/main/README.md", None)
    _, outputs, images = Clipper().clip(
        url=CLIPIT_URL,
        use_readability_js=True,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["stdout.md"],
        download_images=True,
    )

    assert outputs[OutputFormat.STDOUT_MD] == raw_readme
    assert images == []


def test_non_markdown_readme_is_converted_from_github_rendering():
    _, outputs, images = Clipper().clip(
        url="https://github.com/python/cpython",
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["stdout.md"],
    )

    assert "# This is Python version" in outputs[OutputFormat.STDOUT_MD]
    assert "\n====================" not in outputs[OutputFormat.STDOUT_MD]
    assert ".. image::" not in outputs[OutputFormat.STDOUT_MD]
    assert images == []


def test_readme_metadata_and_saving_preserve_repository_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = f"{HELLO_WORLD_URL}.git"
    Clipper().clip_and_save(
        url=url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=True,
        include_title=True,
        yaml_frontmatter=True,
        output_formats=["md"],
        create_domain_subdir=True,
        overwrite=False,
    )

    markdown = (tmp_path / "github.com" / "octocatHello-World.md").read_text()
    metadata = yaml.safe_load(markdown.split("---", 2)[1])
    assert metadata["title"] == "octocat/Hello-World"
    assert metadata["source"] == url
    assert "# octocat/Hello-World\n\n" in markdown
    assert f"[Source]({url})\n\nHello World!\n" in markdown


def test_mixed_outputs_use_raw_readme_and_webpage_html():
    _, outputs, images = Clipper().clip(
        url=HELLO_WORLD_URL,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=["md", "stdout.md", "html", "raw.html"],
    )

    assert set(outputs) == set(OutputFormat)
    assert outputs[OutputFormat.MD] == outputs[OutputFormat.STDOUT_MD] == "Hello World!\n"
    assert "Hello World!" in outputs[OutputFormat.READABLE_HTML]
    raw_html = BeautifulSoup(outputs[OutputFormat.RAW_HTML], "html.parser")
    assert raw_html.title is not None
    assert "GitHub" in raw_html.title.get_text()
    assert images == []


def test_html_only_keeps_webpage_extraction_without_readme_warning(caplog):
    _, outputs, _ = Clipper().clip(
        url="https://github.com/octocat/octocat.github.io",
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
    url = "https://github.com/octocat/octocat.github.io"
    title, outputs, images = Clipper().clip(
        url=url,
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
    assert f"No README found for {url}; falling back to webpage extraction." in caplog.text


def test_cli_help_uses_platform_independent_readme_option():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0, result.output
    assert "--use-readme / --no-use-readme" in result.stdout
    assert "--github-readme" not in result.stdout


def test_cli_defaults_to_readme_and_can_opt_out():
    args = [
        HELLO_WORLD_URL,
        "--no-use-readability-js",
        "--no-yaml-frontmatter",
        "--no-include-title",
        "-f",
        "stdout.md",
    ]
    readme_result = CliRunner().invoke(main, args)
    webpage_result = CliRunner().invoke(main, [*args, "--no-use-readme"])

    assert readme_result.exit_code == 0, readme_result.output
    assert readme_result.stdout.strip() == "Hello World!"
    assert webpage_result.exit_code == 0, webpage_result.output
    assert "Hello World!" in webpage_result.stdout
    assert webpage_result.stdout != readme_result.stdout


def test_library_can_opt_out_of_readme_when_saving(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Clipper().clip_and_save(
        url=HELLO_WORLD_URL,
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
    markdown = files[0].read_text()
    assert "Hello World!" in markdown
    assert markdown != "Hello World!\n"


def test_github_download_failure_keeps_cli_bookmark_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = "https://github.com/octocat/clipit-repository-that-does-not-exist"
    result = CliRunner().invoke(
        main,
        [url, "--bookmark-on-failure", "--title", "Repository", "--notes", "Read later.", "-f", "stdout.md"],
    )

    assert result.exit_code == 0, result.output
    metadata = yaml.safe_load(result.stdout.split("---", 2)[1])
    assert metadata["source"] == url
    assert metadata["title"] == "Repository"
    assert "Read later." in result.stdout
    assert "404" in result.stderr
    assert not list(tmp_path.iterdir())


def test_readme_and_webpage_images_are_saved_with_valid_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Clipper().clip_and_save(
        url=CLIPIT_URL,
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

    output_dir = tmp_path / "github.com"
    file_name = sanitize_filename("vladiliescu/clipit")
    markdown = (output_dir / f"{file_name}.md").read_text()
    readable_html = BeautifulSoup((output_dir / f"{file_name}.html").read_text(), "html.parser")
    raw_html = BeautifulSoup((output_dir / f"{file_name}.raw.html").read_text(), "html.parser")
    assert "../attachments/github.com/" in markdown
    image_paths = list((tmp_path / "attachments" / "github.com" / file_name).iterdir())
    assert len(image_paths) >= 2
    assert all(path.read_bytes() for path in image_paths)
    markdown_images = [
        child.attrGet("src")
        for token in MarkdownIt().enable("table").parse(markdown)
        for child in token.children or []
        if child.type == "image"
    ]
    assert len(markdown_images) >= 2
    for src in markdown_images:
        assert isinstance(src, str)
        assert (output_dir / unquote(src)).resolve() in image_paths
    assert readable_html.find_all("img")
    for image in readable_html.find_all("img"):
        src = str(image["src"])
        if not urlparse(src).scheme:
            assert (output_dir / unquote(src)).resolve() in image_paths
    assert any(urlparse(str(image.get("src", ""))).scheme for image in raw_html.find_all("img"))
