# Tests that the outputs returned by Grabber.grab match exactly the requested output formats
from __future__ import annotations

import pytest
from grabit_md.core.output_format import OutputFormat
from grabit_md.grabber import Grabber


@pytest.mark.parametrize(
    "requested_formats, expected_keys",
    [
        ([(OutputFormat.MD.value)], {OutputFormat.MD}),
        ([(OutputFormat.STDOUT_MD.value)], {OutputFormat.STDOUT_MD}),
        (
            [OutputFormat.MD.value, OutputFormat.STDOUT_MD.value],
            {OutputFormat.MD, OutputFormat.STDOUT_MD},
        ),
    ],
)
def test_grab_outputs_match_requested_formats(requested_formats: list[str], expected_keys: set[OutputFormat]):
    url = "https://example.com/"
    grabber = Grabber()

    title, outputs = grabber.grab(
        url=url,
        use_readability_js=False,
        fallback_title="Untitled {date}",
        include_source=False,
        include_title=False,
        yaml_frontmatter=False,
        output_formats=requested_formats,
    )

    assert isinstance(title, str)

    returned_keys = set(outputs.keys())
    assert returned_keys == expected_keys, (
        f"Returned formats {sorted(map(str, returned_keys))} do not match requested {sorted(requested_formats)}"
    )

    # Additionally, ensure each requested format has non-empty content
    for fmt in expected_keys:
        assert fmt in outputs
        assert isinstance(outputs[fmt], str)
        assert outputs[fmt] != ""
