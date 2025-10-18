from grabit_lib.core import OutputFormat, OutputFormatList, RenderFlags
from grabit_lib.grabbers import BaseGrabber, RedditGrabber

grabbers = [RedditGrabber(), BaseGrabber()]


class Grabber:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    def grab(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: list[str],
    ) -> tuple[str, dict[OutputFormat, str]]:
        grabber = next((g for g in grabbers if g.can_handle(url)), None)
        if grabber is None:
            raise ValueError("No grabber found for the given URL.")

        output_format_list: OutputFormatList = OutputFormatList(output_formats)

        return grabber.grab(url, self.user_agent, use_readability_js, fallback_title, render_flags, output_format_list)

    def grab_and_save(self, url: str) -> str:
        data = self.grab(url)
        return f"Data saved: {data}"
