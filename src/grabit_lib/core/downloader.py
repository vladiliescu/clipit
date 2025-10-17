import requests
from requests import RequestException

from grabit_lib.core import GrabitError


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
        raise GrabitError(f"Error downloading {url}: {e}")

    return html_content
