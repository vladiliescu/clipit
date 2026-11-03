import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from clipit.core import OutputFormat, OutputFormatList, RenderFlags
from clipit.core.downloader import download_html_content
from clipit.core.image_processor import process_images
from clipit.core.markdown_converter import convert_to_markdown
from clipit.core.paths import get_image_directory
from clipit.grabbers.base_grabber import BaseGrabber


@dataclass
class ReadmeSource:
    title: str
    url: str
    content: str | None = None
    frontmatter: str = ""


class ReadmeGrabber(BaseGrabber):
    def can_handle_request(self, url: str, *, use_readme: bool = True) -> bool:
        return use_readme and self.can_handle(url)

    def _get_readme(self, url: str, user_agent: str | None) -> ReadmeSource | None:
        raise NotImplementedError

    def _get_readme_html(
        self,
        url: str,
        user_agent: str | None,
        page_html: str | None,
    ) -> str:
        raise NotImplementedError

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

        readme = self._get_readme(url, user_agent)
        if readme is None:
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

        should_download_images = download_images and any(fmt.is_file_output() for fmt in output_formats)
        markdown_readme = Path(urlparse(readme.url).path).suffix.lower() in {
            "",
            ".md",
            ".markdown",
            ".mdown",
            ".mkd",
            ".mkdn",
            ".mdwn",
            ".txt",
        }
        should_render_readme = should_download_images or not markdown_readme
        outputs: dict[OutputFormat, str] = {}
        images: list[tuple[str, bytes]] = []
        page_html: str | None = None
        html_formats = [fmt.value for fmt in output_formats if fmt in {OutputFormat.READABLE_HTML, OutputFormat.RAW_HTML}]
        if html_formats:
            # Providers can reuse the downloaded webpage when rendering a README.
            if should_render_readme and OutputFormat.RAW_HTML.value not in html_formats:
                html_formats.append(OutputFormat.RAW_HTML.value)
            _, outputs, _ = super().grab(
                url,
                user_agent,
                use_readability_js,
                fallback_title,
                render_flags,
                OutputFormatList(html_formats),
                False,
            )
            page_html = outputs.get(OutputFormat.RAW_HTML)
            if OutputFormat.RAW_HTML in outputs and OutputFormat.RAW_HTML not in output_formats:
                del outputs[OutputFormat.RAW_HTML]

        if should_render_readme:
            readme_html = self._get_readme_html(url, user_agent, page_html)
            if should_download_images:
                directory = get_image_directory(readme.title, url, download_folder, output_dir)
                image_url_to_filename: dict[str, str] = {}
                readme_html, images = process_images(
                    readme_html, readme.title, readme.url, user_agent, directory, image_url_to_filename
                )
                if OutputFormat.READABLE_HTML in outputs:
                    outputs[OutputFormat.READABLE_HTML], html_images = process_images(
                        outputs[OutputFormat.READABLE_HTML],
                        readme.title,
                        url,
                        user_agent,
                        directory,
                        image_url_to_filename,
                    )
                    images.extend(html_images)
            markdown_content = convert_to_markdown(readme_html)
            if readme.frontmatter:
                markdown_content = f"{readme.frontmatter}\n{markdown_content}"
        else:
            markdown_content = (
                readme.content if readme.content is not None else download_html_content(readme.url, user_agent)
            )

        markdown_content = self.post_process_markdown(url, readme.title, markdown_content, render_flags)
        if output_formats.should_output_markdown_file():
            outputs[OutputFormat.MD] = markdown_content
        if output_formats.should_output_markdown_stdout():
            outputs[OutputFormat.STDOUT_MD] = markdown_content

        return readme.title, outputs, images
