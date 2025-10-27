from clipit.core import OutputFormat, OutputFormatList
from clipit.core.dtos import RenderFlags
from clipit.core.writer import output
from clipit.grabbers import BaseGrabber, RedditGrabber

grabbers: list[BaseGrabber] = [RedditGrabber(), BaseGrabber()]


class Clipper:
    def __init__(self, user_agent: str | None = None):
        self.user_agent = user_agent

    def clip(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        include_source: bool,
        include_title: bool,
        yaml_frontmatter: bool,
        output_formats: list[str],
    ) -> tuple[str, dict[OutputFormat, str]]:
        grabber = next((g for g in grabbers if g.can_handle(url)), None)
        if grabber is None:
            raise ValueError("No grabber found for the given URL.")

        output_format_list: OutputFormatList = OutputFormatList(output_formats)
        render_flags = RenderFlags(
            include_source=include_source,
            include_title=include_title,
            yaml_frontmatter=yaml_frontmatter,
        )

        return grabber.grab(url, self.user_agent, use_readability_js, fallback_title, render_flags, output_format_list)

    def clip_and_save(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        include_source: bool,
        include_title: bool,
        yaml_frontmatter: bool,
        output_formats: list[str],
        create_domain_subdir: bool,
        overwrite: bool,
    ) -> None:
        title, outputs = self.clip(
            url, use_readability_js, fallback_title, include_source, include_title, yaml_frontmatter, output_formats
        )
        output(title, outputs, url, create_domain_subdir, overwrite)
