from readabilipy import simple_json_from_html_string

from grabit_md import GrabitError


def extract_readable_content_and_title(html_content, use_readability_js):
    try:
        rpy = simple_json_from_html_string(html_content, use_readability=use_readability_js)
        content_html = rpy.get("content") or ""

        # If readability.js fails, try again without it
        if not content_html and use_readability_js:
            rpy = simple_json_from_html_string(html_content, use_readability=False)
            content_html = rpy.get("content", "")
            if not content_html:
                raise GrabitError("No content found")

        content_html = content_html.replace(
            'href="about:blank/', 'href="../'
        )  # Fix for readability replacing ".." with "about:blank"
        title = (rpy.get("title") or "").strip()
    except Exception as e:
        raise GrabitError(f"Error processing HTML content: {e}")
    return (
        content_html,
        title,
    )
