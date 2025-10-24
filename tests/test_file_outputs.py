import pytest
from grabit_md.core.writer import sanitize_filename


@pytest.mark.parametrize(
    "input_filename, expected_output",
    [
        ("invalid|file:name.txt", "invalidfilename.txt"),
        ("another/invalid\\name.txt", "anotherinvalidname.txt"),
        ("valid_name.txt", "valid_name.txt"),
    ],
)
def test_sanitize_filename_should_work(input_filename, expected_output):
    assert sanitize_filename(input_filename) == expected_output


def test_sanitize_filename_should_not_create_hidden_files():
    assert sanitize_filename(".NET Core") == "NET Core"
