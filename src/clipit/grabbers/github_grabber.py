import json
import re
from urllib.parse import urlparse

from requests import HTTPError

from clipit.core import ClipitError, DownloadError
from clipit.core.downloader import download_html_content
from clipit.grabbers.readme_grabber import ReadmeGrabber, ReadmeSource


class GitHubGrabber(ReadmeGrabber):
    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            return False
        match = re.fullmatch(r"/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?", parsed.path)
        if match is None:
            return False
        return match[1].lower() not in {
            "about",
            "account",
            "apps",
            "codespaces",
            "collections",
            "contact",
            "copilot",
            "customer-stories",
            "education",
            "enterprise",
            "features",
            "issues",
            "join",
            "login",
            "marketplace",
            "new",
            "notifications",
            "open-source",
            "organizations",
            "orgs",
            "pricing",
            "pulls",
            "readme",
            "resources",
            "search",
            "security",
            "settings",
            "site",
            "solutions",
            "sponsors",
            "topics",
            "trending",
            "users",
        }

    def _get_readme(self, url: str, user_agent: str | None) -> ReadmeSource | None:
        repository = urlparse(url).path.strip("/").removesuffix(".git")
        readme_api_url = f"https://api.github.com/repos/{repository}/readme"
        try:
            readme_response = download_html_content(readme_api_url, user_agent, accept="application/vnd.github+json")
        except DownloadError as exc:
            cause = exc.__cause__
            if not isinstance(cause, HTTPError) or cause.response is None or cause.response.status_code != 404:
                raise
            return None

        try:
            readme = json.loads(readme_response)
        except json.JSONDecodeError as exc:
            raise ClipitError(f"Invalid GitHub README response for {url}: {exc}") from exc
        if not isinstance(readme, dict) or not isinstance(readme.get("download_url"), str):
            raise ClipitError(f"GitHub did not provide a README download URL for {url}.")
        readme_url = readme["download_url"]
        if not readme_url:
            raise ClipitError(f"GitHub did not provide a README download URL for {url}.")

        return ReadmeSource(repository, readme_url)

    def _get_readme_html(self, url: str, user_agent: str | None, page_html: str | None) -> str:
        repository = urlparse(url).path.strip("/").removesuffix(".git")
        return download_html_content(
            f"https://api.github.com/repos/{repository}/readme", user_agent, accept="application/vnd.github.html+json"
        )
