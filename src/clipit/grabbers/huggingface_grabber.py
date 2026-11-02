import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import HTTPError

from clipit.core import ClipitError, DownloadError
from clipit.core.downloader import download_html_content
from clipit.grabbers.readme_grabber import ReadmeGrabber, ReadmeSource


class HuggingFaceGrabber(ReadmeGrabber):
    def can_handle(self, url: str, *, use_readme: bool = True) -> bool:
        if not use_readme:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"huggingface.co", "hf.co"}:
            return False
        match = re.fullmatch(
            r"/(datasets/)?([A-Za-z0-9_][A-Za-z0-9_.-]*)/([A-Za-z0-9_][A-Za-z0-9_.-]*)/?", parsed.path
        )
        if match is None:
            return False
        return match[1] is not None or match[2].lower() not in {
            "api",
            "blog",
            "collections",
            "contact",
            "datasets",
            "docs",
            "enterprise",
            "inference",
            "join",
            "learn",
            "login",
            "models",
            "oauth",
            "organizations",
            "papers",
            "pricing",
            "search",
            "settings",
            "spaces",
            "tasks",
            "users",
        }

    def _get_readme(self, url: str, user_agent: str | None) -> ReadmeSource | None:
        repository = urlparse(url).path.strip("/").removesuffix(".git")
        readme_url = f"https://huggingface.co/{repository}/raw/main/README.md"
        try:
            content = download_html_content(readme_url, user_agent)
        except DownloadError as exc:
            cause = exc.__cause__
            if (
                not isinstance(cause, HTTPError)
                or cause.response is None
                or cause.response.status_code != 404
                or cause.response.headers.get("X-Error-Code") != "EntryNotFound"
            ):
                raise
            return None

        frontmatter = re.match(r"\A---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)", content, re.MULTILINE | re.DOTALL)
        return ReadmeSource(repository, readme_url, content, frontmatter[0] if frontmatter else "")

    def _get_readme_html(self, url: str, user_agent: str | None, page_html: str | None) -> str:
        if page_html is None:
            page_html = download_html_content(url, user_agent)
        card = BeautifulSoup(page_html, "html.parser").select_one("main .prose")
        if card is None:
            raise ClipitError(f"No rendered Hugging Face README found for {url}.")
        return str(card)
