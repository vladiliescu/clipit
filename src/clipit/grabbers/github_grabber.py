import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from requests import HTTPError

from clipit.core import ClipitError, DownloadError, OutputFormat, OutputFormatList, RenderFlags
from clipit.core.downloader import download_html_content
from clipit.core.image_processor import process_images
from clipit.core.markdown_converter import convert_to_markdown
from clipit.core.paths import get_image_directory
from clipit.grabbers.base_grabber import BaseGrabber


class GitHubGrabber(BaseGrabber):
    def can_handle(self, url: str, *, use_readme: bool = True) -> bool:
        if not use_readme:
            return False
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

    def grab(
        self,
        url: str,
        user_agent: str | None,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: OutputFormatList,
        download_images: bool,
        download_folder: str | None = None,
        output_dir: Path = Path("."),
    ) -> tuple[str, dict[OutputFormat, str], list[tuple[str, bytes]]]:
        if not output_formats.should_output_markdown():
            return super().grab(
                url,
                user_agent,
                use_readability_js,
                fallback_title,
                render_flags,
                output_formats,
                download_images,
                download_folder,
                output_dir,
            )

        repository = urlparse(url).path.strip("/").removesuffix(".git")
        readme_api_url = f"https://api.github.com/repos/{repository}/readme"
        try:
            readme_response = download_html_content(readme_api_url, user_agent, accept="application/vnd.github+json")
        except DownloadError as exc:
            cause = exc.__cause__
            if not isinstance(cause, HTTPError) or cause.response is None or cause.response.status_code != 404:
                raise
            logging.getLogger(__name__).warning("No README found for %s; falling back to webpage extraction.", url)
            return super().grab(
                url,
                user_agent,
                use_readability_js,
                fallback_title,
                render_flags,
                output_formats,
                download_images,
                download_folder,
                output_dir,
            )

        try:
            readme = json.loads(readme_response)
        except json.JSONDecodeError as exc:
            raise ClipitError(f"Invalid GitHub README response for {url}: {exc}") from exc
        if not isinstance(readme, dict) or not isinstance(readme.get("download_url"), str):
            raise ClipitError(f"GitHub did not provide a README download URL for {url}.")
        readme_url = readme["download_url"]
        if not readme_url:
            raise ClipitError(f"GitHub did not provide a README download URL for {url}.")

        outputs: dict[OutputFormat, str] = {}
        images: list[tuple[str, bytes]] = []
        html_formats = OutputFormatList(
            [fmt.value for fmt in output_formats if fmt in {OutputFormat.READABLE_HTML, OutputFormat.RAW_HTML}]
        )
        if len(html_formats):
            _, outputs, _ = super().grab(
                url,
                user_agent,
                use_readability_js,
                fallback_title,
                render_flags,
                html_formats,
                False,
            )

        should_download_images = download_images and any(fmt.is_file_output() for fmt in output_formats)
        markdown_readme = Path(urlparse(readme_url).path).suffix.lower() in {
            "",
            ".md",
            ".markdown",
            ".mdown",
            ".mkd",
            ".mkdn",
            ".mdwn",
            ".txt",
        }
        if should_download_images or not markdown_readme:
            readme_html = download_html_content(readme_api_url, user_agent, accept="application/vnd.github.html+json")
            if should_download_images:
                directory = get_image_directory(repository, url, download_folder, output_dir)
                image_url_to_filename: dict[str, str] = {}
                readme_html, images = process_images(
                    readme_html, repository, readme_url, user_agent, directory, image_url_to_filename
                )
                if OutputFormat.READABLE_HTML in outputs:
                    outputs[OutputFormat.READABLE_HTML], html_images = process_images(
                        outputs[OutputFormat.READABLE_HTML], repository, url, user_agent, directory, image_url_to_filename
                    )
                    images.extend(html_images)
            markdown_content = convert_to_markdown(readme_html)
        else:
            markdown_content = download_html_content(readme_url, user_agent)

        markdown_content = self.post_process_markdown(url, repository, markdown_content, render_flags)
        if output_formats.should_output_markdown_file():
            outputs[OutputFormat.MD] = markdown_content
        if output_formats.should_output_markdown_stdout():
            outputs[OutputFormat.STDOUT_MD] = markdown_content

        return repository, outputs, images
