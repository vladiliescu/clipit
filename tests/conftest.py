import gzip
import json
import shutil
import ssl
import subprocess
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest


@pytest.fixture(scope="session")
def saved_page_expectations():
    fixtures = Path(__file__).parent / "fixtures"
    expected = {
        page: json.loads((fixtures / f"{page}.json").read_text()) for page in ("example-domain", "boring-table")
    }
    title_data: list[str] = []

    class TitleParser(HTMLParser):
        def handle_data(self, data: str) -> None:
            title_data.append(data)

    # CPython gh-118350 makes markup inside <title> literal text.
    TitleParser().feed("<title><p>Example Domain</p></title>")
    assert title_data in (["Example Domain"], ["<p>Example Domain</p>"])
    if title_data == ["<p>Example Domain</p>"]:
        expected["example-domain"]["python"]["md"] = expected["example-domain"]["python"]["md_rcdata"]
    return expected


@pytest.fixture
def page_server(tmp_path):
    directory = tmp_path / "pages"
    directory.mkdir()
    for filename in ("example-domain.html", "boring-table.html"):
        (directory / filename).write_bytes((Path(__file__).parent / "fixtures" / filename).read_bytes())

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/example-domain.html")
                self.end_headers()
            elif self.path == "/compressed":
                content = gzip.compress((directory / "example-domain.html").read_bytes())
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                super().do_GET()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def untrusted_https_server(tmp_path):
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL is required to generate the local TLS certificate")

    certificate = tmp_path / "certificate.pem"
    key = tmp_path / "key.pem"
    subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"https://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def image_server(tmp_path):
    directory = tmp_path / "http"
    directory.mkdir()
    image_bytes = (Path(__file__).parent / "fixtures" / "outlive.jpg").read_bytes()
    for filename in ("photo.JPEG", "converted.png", "banner"):
        (directory / filename).write_bytes(image_bytes)
    received_requests = []

    class Handler(SimpleHTTPRequestHandler):
        # A CDN can return JPEG content even when its URL ends in .png.
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".png": "image/jpeg"}

        def do_GET(self):
            received_requests.append(self.path)
            super().do_GET()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", directory, received_requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
