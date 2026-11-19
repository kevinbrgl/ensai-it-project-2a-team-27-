"""Serve the compiled Ex-Libris frontend and forward API requests.

Run ``python app.py`` from the frontend directory. The server works at
the site root and behind the Onyxia or VS Code proxy.

The ``BACKEND_URL`` environment variable defaults to
``http://127.0.0.1:8000``. ``FRONTEND_PORT`` defaults to ``5000``.
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
    """Serve frontend assets and forward API requests to FastAPI."""

    def _strip_prefix(self) -> None:
        """Remove the Onyxia proxy prefix from the request path."""
        self.path = PREFIX.sub("", self.path, count=1) or "/"

    # --- API proxy -----------------------------------------------------
    def _proxy(self) -> None:
        """Forward the request and write the backend response to the client."""
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
        """Serve an asset or fall back to the React app for client routes."""
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
        """Dispatch HTTP requests to the API proxy or static file server."""
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
        """Write one line with the request method, path, and status.

        Parameters
        ----------
        _format : str
            Message format supplied by the base handler, which is ignored.
        *args : object
            Log arguments from the base handler. The second item, when
            present, is used as the response status.

        """
        status = args[1] if len(args) > 1 else ""
        sys.stderr.write(f"  {self.command} {self.path} -> {status}\n")

    def end_headers(self) -> None:
        """Set cache headers before sending the response headers.

        Cache build assets for one year and require revalidation for other
        frontend files, including ``index.html``.
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
    """Validate the configuration and serve the app until interrupted.

    Exit with an error if the backend URL lacks an HTTP scheme or the
    frontend build cannot be found.
    """
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
