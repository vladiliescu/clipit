from enum import Enum


class OutputFormat(Enum):
    MD = "md"
    STDOUT_MD = "stdout.md"
    READABLE_HTML = "html"
    RAW_HTML = "raw.html"

    def __str__(self):
        return self.value

    def is_file_output(self) -> bool:
        """Check if this format should be written to a file (vs stdout)."""
        return "stdout" not in self.value


class OutputFormatList:
    def __init__(self, formats: list[str]):
        self._formats: list[OutputFormat] = [OutputFormat(fmt) for fmt in formats]

    def __iter__(self):
        return iter(self._formats)

    def __contains__(self, item: OutputFormat) -> bool:
        return item in self._formats

    def __len__(self) -> int:
        return len(self._formats)

    def should_output_raw_html(self) -> bool:
        return OutputFormat.RAW_HTML in self._formats

    def should_output_readable_html(self) -> bool:
        return OutputFormat.READABLE_HTML in self._formats

    def should_output_markdown(self) -> bool:
        return OutputFormat.MD in self._formats or OutputFormat.STDOUT_MD in self._formats

    def should_output_markdown_file(self) -> bool:
        return OutputFormat.MD in self._formats

    def should_output_markdown_stdout(self) -> bool:
        return OutputFormat.STDOUT_MD in self._formats
