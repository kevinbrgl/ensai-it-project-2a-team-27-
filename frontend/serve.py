"""Serve the built Ex-Libris frontend with Python only (no Node.js needed).

- Serves the compiled React app from the ``dist/`` folder.
- Forwards every ``/api/...`` request to the FastAPI backend, so the browser
  talks to a single origin (the backend has no CORS configuration).
- Works at the site root and behind the Onyxia/VSCode ``/proxy/<port>/`` or
  ``/absproxy/<port>/`` URLs.

Usage (from this folder):

    python serve.py

Settings, through environment variables:

    BACKEND_URL    FastAPI address   (default http://127.0.0.1:8000)
    FRONTEND_PORT  port to listen on (default 5173)
"""

import os
import re
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
PORT = int(os.environ.get("FRONTEND_PORT", "5173"))

# Onyxia's /absproxy/<port>/ keeps this prefix in the path; drop it.
PREFIX = re.compile(r"^/(?:abs)?proxy/\d+(?=/)")
# Headers that must not be copied between connections.
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class FrontendHandler(SimpleHTTPRequestHandler):
    """Static files from dist/, with /api forwarded to the backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def _strip_prefix(self) -> None:
        self.path = PREFIX.sub("", self.path, count=1) or "/"

    # --- API proxy -----------------------------------------------------
    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        request = urllib.request.Request(
            BACKEND_URL + self.path, data=body, method=self.command,
        )
        for name, value in self.headers.items():
            if name.lower() not in HOP_BY_HOP:
                request.add_header(name, value)
        try:
            response = urllib.request.urlopen(request, timeout=30)
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
        elif self.command in ("GET", "HEAD"):
            self._serve_static()
        else:
            self.send_error(405)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

    def log_message(self, format: str, *args) -> None:  # quieter logs
        sys.stderr.write(f"  {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")


def main() -> None:
    if not (DIST / "index.html").is_file():
        sys.exit(
            "The dist/ folder is missing. It contains the compiled app; "
            "rebuild it with `npm install && npm run build`.",
        )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), FrontendHandler)
    print(f"Ex-Libris frontend on http://localhost:{PORT}  (API -> {BACKEND_URL})")
    print("On Onyxia, open <your VSCode URL>/proxy/" f"{PORT}/   —   Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
