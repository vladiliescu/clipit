import json
import re
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import click
import requests
import yaml
from click import ClickException
from markdownify import (
    ATX,
    UNDERSCORE,
    MarkdownConverter,
    abstract_inline_conversion,  # type: ignore
)
from mdformat import text as mdformat_text
from readabilipy import simple_json_from_html_string
from requests import RequestException

from grabit_lib.core import OutputFormat, OutputFormatList

VERSION = version("grabit-lib")


@dataclass
class RenderFlags:
    include_source: bool
    include_title: bool
    yaml_frontmatter: bool


@dataclass
class OutputFlags:
    output_formats: OutputFormatList
    create_domain_subdir: bool
    overwrite: bool


def should_output_file(output_formats):
    return any("stdout" not in fmt.value for fmt in output_formats)


class BaseGrabber:
    def can_handle(self, url: str) -> bool:
        return True

    def grab(
        self,
        url: str,
        user_agent: str,
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

            outputs[OutputFormat.MD] = markdown_content
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


class RedditGrabber(BaseGrabber):
    def can_handle(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return domain == "www.reddit.com" or domain == "old.reddit.com"

    def grab(
        self,
        url: str,
        user_agent: str,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: OutputFormatList,
    ) -> tuple[str, dict[OutputFormat, str]]:
        if (
            output_formats.should_output_raw_html()
            or output_formats.should_output_readable_html()
            or not output_formats.should_output_markdown()
        ):
            raise ClickException("Reddit posts can only be converted to Markdown.")

        outputs = {}

        json_url = self._convert_to_json_url(url)
        json_content = json.loads(download_html_content(json_url, user_agent))

        title = json_content[0]["data"]["children"][0]["data"].get("title", None)
        title = self.post_process_title(title, fallback_title)

        markdown_content = self._reddit_json_to_markdown(json_content)
        markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

        outputs[OutputFormat.MD] = markdown_content
        outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs

    def _convert_to_json_url(self, url):
        parsed_url = urlparse(url)

        path = parsed_url.path.rstrip("/")
        new_path = f"{path}.json"

        json_url = urlunparse(parsed_url._replace(path=new_path))
        return json_url

    def _reddit_json_to_markdown(self, reddit_post_json):
        def parse_comments(comments_data, depth=0):
            comments_md = ""
            # Sort comments by score, highest first
            sorted_comments = sorted(comments_data, key=lambda x: x["data"].get("score", 0), reverse=True)
            for comment in sorted_comments:
                comment_data = comment["data"]
                author = comment_data.get("author", "[deleted]")
                score = comment_data.get("score", 0)
                body = comment_data.get("body", "").replace("\n", "\n" + "    " * (depth + 1))
                indentation = "    " * depth

                comments_md += f"{indentation}- **{author}** [{score} score]:\n{indentation}    {body}\n\n"

                # Check if 'replies' is a dict (has replies), and recursively parse them
                if isinstance(comment_data.get("replies"), dict):
                    nested_comments = comment_data["replies"]["data"]["children"]
                    comments_md += parse_comments(nested_comments, depth + 1)

            return comments_md

        try:
            # Extract post information
            post_data = reddit_post_json[0]["data"]["children"][0]["data"]
            selftext = post_data.get("selftext", "").replace("\n", "\n> ")
            post_url = post_data.get("url", "")  # needed for link posts
            author = post_data.get("author", "[deleted]")
            score = post_data.get("score", 0)

            markdown = f"**{author}** [{score} score]:\n> {selftext if selftext else post_url}\n\n"

            # Extract comments
            comments_data = reddit_post_json[1]["data"]["children"]
            markdown += "## Comments\n\n"
            markdown += parse_comments(comments_data)

        except Exception as e:
            raise ClickException(f"Error converting Reddit JSON to Markdown: {e}")

        return markdown


grabbers = [RedditGrabber()]


def output(title: str, outputs: dict[OutputFormat, str], url: str, output_flags: OutputFlags):
    output_dir = None
    safe_title = None

    if should_output_file(outputs):
        if output_flags.create_domain_subdir:
            output_dir = create_output_dir(url)
        else:
            output_dir = Path(".")
        safe_title = sanitize_filename(title)

    for fmt in output_flags.output_formats:
        content = outputs.get(fmt)
        if should_output_file([fmt]):
            # output_dir and safe_title are only defined if we're saving to a file
            if content is not None and output_dir is not None and safe_title is not None:
                write_to_file(content, str(output_dir), safe_title, fmt.value, output_flags.overwrite)
        else:
            if content is not None:
                click.echo(content)


def sanitize_filename(filename):
    # Remove Obsidian-specific characters
    sanitized = re.sub(r"[#|\^\[\]]", "", filename)

    # Most conservative approach - remove all problematic characters including control characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", sanitized)

    # Handle Windows reserved filenames
    sanitized = re.sub(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", r"_\1\2", sanitized, flags=re.IGNORECASE)

    # Remove trailing spaces and periods
    sanitized = re.sub(r"[\s.]+$", "", sanitized)

    # Remove leading periods
    sanitized = re.sub(r"^\.+", "", sanitized)

    # Trim to 240 characters to leave room for extensions
    sanitized = sanitized[:240]

    return sanitized


def try_include_title(include_title, markdown_content, title):
    if include_title:
        markdown_content = f"# {title}\n\n{markdown_content}"
    return markdown_content


def try_include_source(include_source, markdown_content, url):
    if include_source:
        markdown_content = f"[Source]({url})\n\n{markdown_content}"
    return markdown_content


def try_add_yaml_frontmatter(yaml_frontmatter: bool, markdown_content, title, url):
    if not yaml_frontmatter:
        return markdown_content

    metadata = {
        "title": title,
        "source": url,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    yaml_metadata = yaml.dump(metadata, sort_keys=False)
    markdown_content = f"---\n{yaml_metadata}---\n\n{markdown_content}"
    return markdown_content


def write_to_file(
    markdown_content: str,
    output_dir: str,
    safe_title: str,
    extension: str,
    overwrite: bool,
):
    output_file = Path(output_dir) / f"{safe_title}.{extension}"

    if not overwrite and output_file.exists():
        click.echo(f"File {output_file} already exists. Use --overwrite to replace it.")
        return

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        click.echo(f"Saved {extension} content to {output_file}")
    except Exception as e:
        raise ClickException(f"Error writing to file {output_file}: {e}")


def create_output_dir(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    if not domain:
        domain = "unknown_domain"
    output_dir = Path(".") / domain
    output_dir.mkdir(exist_ok=True, parents=True)

    return output_dir


class GrabitMarkdownConverter(MarkdownConverter):
    def convert_em(self, el, text, parent_tags):
        return self.convert_i(el, text, parent_tags)

    def convert_i(self, el, text, parent_tags):
        """I like my bolds ** and my italics _."""
        return abstract_inline_conversion(lambda s: UNDERSCORE)(self, el, text, parent_tags)


def convert_to_markdown(content_html):
    converter = GrabitMarkdownConverter(heading_style=ATX, bullets="-")
    markdown_content = converter.convert(content_html)
    pretty_markdown_content = mdformat_text(markdown_content)
    return pretty_markdown_content


def extract_readable_content_and_title(html_content, use_readability_js):
    try:
        rpy = simple_json_from_html_string(html_content, use_readability=use_readability_js)
        content_html = rpy.get("content") or ""

        # If readability.js fails, try again without it
        if not content_html and use_readability_js:
            rpy = simple_json_from_html_string(html_content, use_readability=False)
            content_html = rpy.get("content", "")
            if not content_html:
                raise ClickException("No content found")

        content_html = content_html.replace(
            'href="about:blank/', 'href="../'
        )  # Fix for readability replacing ".." with "about:blank"
        title = (rpy.get("title") or "").strip()
    except Exception as e:
        raise ClickException(f"Error processing HTML content: {e}")
    return (
        content_html,
        title,
    )


def download_html_content(url, user_agent: str) -> str:
    try:
        request_headers = {
            "User-Agent": user_agent,
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(url, headers=request_headers)
        response.raise_for_status()
        html_content = response.content.decode("utf-8")
    except RequestException as e:
        raise ClickException(f"Error downloading {url}: {e}")
    return html_content
