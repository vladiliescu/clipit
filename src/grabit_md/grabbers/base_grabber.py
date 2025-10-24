from datetime import datetime

from grabit_md.core import OutputFormat, OutputFormatList, RenderFlags
from grabit_md.core.downloader import download_html_content
from grabit_md.core.extractor import extract_readable_content_and_title
from grabit_md.core.markdown_converter import (
    convert_to_markdown,
    try_add_yaml_frontmatter,
    try_include_source,
    try_include_title,
)


class BaseGrabber:
    def can_handle(self, url: str) -> bool:
        return True

    def grab(
        self,
        url: str,
        user_agent: str | None,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: OutputFormatList,
    ) -> tuple[str, dict[OutputFormat, str]]:
        outputs = {}

        html_content = download_html_content(url, user_agent)
        if output_formats.should_output_raw_html():
            outputs[OutputFormat.RAW_HTML] = html_content

        html_readable_content, title = extract_readable_content_and_title(html_content, use_readability_js)
        title = self.post_process_title(title, fallback_title)

        if output_formats.should_output_readable_html():
            outputs[OutputFormat.READABLE_HTML] = html_readable_content

        if output_formats.should_output_markdown():
            markdown_content = convert_to_markdown(html_readable_content)
            markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

            if output_formats.should_output_markdown_file():
                outputs[OutputFormat.MD] = markdown_content

            if output_formats.should_output_markdown_stdout():
                outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs

    def render_markdown(self, markdown_content):
        return markdown_content

    def handle_missing_title(self, title: str, fallback_title: str):
        if not title:
            title = fallback_title.format(date=datetime.now().strftime("%Y-%m-%d"))

        return title

    def post_process_markdown(
        self,
        url: str,
        title: str,
        markdown_content: str,
        render_flags: RenderFlags,
    ):
        markdown_content = try_include_source(render_flags.include_source, markdown_content, url)
        markdown_content = try_include_title(render_flags.include_title, markdown_content, title)
        markdown_content = try_add_yaml_frontmatter(render_flags.yaml_frontmatter, markdown_content, title, url)

        return markdown_content

    def post_process_title(self, title: str, fallback_title: str):
        title = self.handle_missing_title(title, fallback_title)

        return title
