"""Ex-Libris frontend with Python only .

- Serves the compiled React app from the ``dist/`` folder.
- Forwards every ``/api/...`` request to the FastAPI backend, so the browser
  talks to a single origin (the backend has no CORS configuration).
- Works at the site root and behind the Onyxia/VSCode ``/proxy/<port>/`` or
  ``/absproxy/<port>/`` URLs.

Usage (from this folder):

    python app.py

Settings, through environment variables:

    BACKEND_URL    FastAPI address   (default http://127.0.0.1:8000)
    FRONTEND_PORT  port to listen on (default 5000)
"""

import os
import re
import sys
import urllib.error
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

DIST = Path(__file__).resolve().parent / "dist"
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
).rstrip("/")
PORT = int(os.environ.get("FRONTEND_PORT", "5000"))
# Listen on every interface: the Onyxia/VSCode proxy must reach the server.
HOST = "0.0.0.0"  # ruff: ignore[hardcoded-bind-all-interfaces]

# Onyxia's /absproxy/<port>/ keeps this prefix in the path; drop it.
PREFIX = re.compile(r"^/(?:abs)?proxy/\d+(?=/)")
# Headers that must not be copied between connections.
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class FrontendHandler(SimpleHTTPRequestHandler):
    """Static files from dist/, with /api forwarded to the backend.

    The dist/ directory is given with functools.partial in main().
    """

    def _strip_prefix(self) -> None:
        self.path = PREFIX.sub("", self.path, count=1) or "/"

    # --- API proxy -----------------------------------------------------
    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        # BACKEND_URL is checked to be http(s) in main().
        req = Request(  # ruff: ignore[suspicious-url-open-usage]
            BACKEND_URL + self.path,
            data=body,
            method=self.command,
        )
        for name, value in self.headers.items():
            if name.lower() not in HOP_BY_HOP:
                req.add_header(name, value)
        try:
            response = urlopen(  # ruff: ignore[suspicious-url-open-usage]
                req,
                timeout=30,
            )
        except urllib.error.HTTPError as error:  # 4xx/5xx: pass them through
            response = error
        except (urllib.error.URLError, OSError):
            message = b'{"detail": "Cannot reach the backend. Is it running?"}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return

        data = response.read()
        self.send_response(response.status)
        for name, value in response.headers.items():
            if name.lower() not in HOP_BY_HOP:
                self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --- Static files with single-page-app fallback ---------------------
    def _serve_static(self) -> None:
        path = self.path.split("?", 1)[0]
        target = DIST / path.lstrip("/")
        if path != "/" and not target.is_file():
            # Unknown paths (e.g. /books/12) are app routes: send index.html.
            self.path = "/index.html"
        if self.command == "HEAD":
            super().do_HEAD()
        else:
            super().do_GET()

    def _handle(self) -> None:
        self._strip_prefix()
        if self.path == "/api" or self.path.startswith("/api/"):
            self._proxy()
        elif self.command in {"GET", "HEAD"}:
            self._serve_static()
        else:
            self.send_error(405)

    # http.server looks these names up, so they must stay in this case.
    do_GET = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]
    do_HEAD = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]
    do_POST = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]
    do_PUT = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]
    do_PATCH = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]
    do_DELETE = _handle  # ruff: ignore[mixed-case-variable-in-class-scope]

    def log_message(self, _format: str, *args: object) -> None:
        """Log one short line per request instead of the default format."""
        status = args[1] if len(args) > 1 else ""
        sys.stderr.write(f"  {self.command} {self.path} -> {status}\n")

    def end_headers(self) -> None:
        """Set cache rules so a new build is picked up on a normal reload.

        index.html must always be revalidated; files in /assets/ have a
        hash in their name, so they can be kept forever.
        """
        if self.path.startswith("/assets/"):
            self.send_header(
                "Cache-Control",
                "public, max-age=31536000, immutable",
            )
        elif not self.path.startswith("/api"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> None:
    """Check the setup, then serve the app until Ctrl+C."""
    if not BACKEND_URL.startswith(("http://", "https://")):
        sys.exit("BACKEND_URL must start with http:// or https://.")
    if not (DIST / "index.html").is_file():
        sys.exit(
            "The dist/ folder is missing. It contains the compiled app; "
            "rebuild it with `npm install && npm run build`.",
        )
    handler = partial(FrontendHandler, directory=str(DIST))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    sys.stdout.write(
        f"Ex-Libris frontend on http://localhost:{PORT}"
        f"  (API -> {BACKEND_URL})\n",
    )
    sys.stdout.write(
        f"On Onyxia, open <your VSCode URL>/proxy/{PORT}/"
        "   —   Ctrl+C to stop.\n",
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nStopped.\n")


if __name__ == "__main__":
    main()
