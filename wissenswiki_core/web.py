"""Slim local web app on the standard library ``http.server``.

Meant for a single user on localhost or a trusted LAN: requests must use the
server's numeric address (or ``localhost`` on loopback), and writes need the
page token plus a matching ``Origin``.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import ipaddress
import json
import secrets
from urllib.parse import parse_qs, quote, urlsplit

from wissenswiki_core.pages import PageUrls, render_page
from wissenswiki_core.registry import Registry
from wissenswiki_core.service import ApiError, api_get, api_post

URLS = PageUrls(api="/api", static="/static/", workspace="/", graph="/graph/",
                graph_header="/graph-header/", settings="/settings/")
ROUTES = {"/": "workspace", "/graph/": "graph", "/graph-header/": "graph-header", "/settings/": "settings"}
CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def static_asset(name: str) -> bytes | None:
    if "/" in name or not name or name.startswith(".") or name[name.rfind("."):] not in CONTENT_TYPES:
        return None
    resource = files("wissenswiki_core").joinpath("static", "wissenswiki", name)
    return resource.read_bytes() if resource.is_file() else None


def make_handler(registry: Registry) -> type[BaseHTTPRequestHandler]:
    token = secrets.token_hex(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "wissenswiki"

        def _send(self, status: int, body: bytes = b"", content_type: str = "text/plain; charset=utf-8",
                  location: str = "") -> None:
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _valid_host(self) -> bool:
            try:
                host = self.headers.get("Host", "")
                parsed = urlsplit("http://" + host)
                if (parsed.netloc != host or parsed.path or parsed.query or parsed.fragment
                        or parsed.username or parsed.password or parsed.port != self.server.server_port):
                    return False
                destination = ipaddress.ip_address(self.connection.getsockname()[0])
                if parsed.hostname == "localhost":
                    return destination.is_loopback
                return ipaddress.ip_address(parsed.hostname) == destination
            except ValueError:
                return False

        def do_GET(self) -> None:
            if not self._valid_host():
                self._json(403, {"error": "Ungültiger Host; bitte die IP-Adresse des Servers verwenden."})
                return
            url = urlsplit(self.path)
            domain = parse_qs(url.query).get("domain", [""])[0]
            if url.path == "/favicon.ico":
                self._send(204)
            elif url.path.startswith(URLS.static + "wissenswiki/"):
                name = url.path.removeprefix(URLS.static + "wissenswiki/")
                body = static_asset(name)
                if body is None:
                    self._send(404, "Nicht gefunden.".encode())
                else:
                    self._send(200, body, CONTENT_TYPES[name[name.rfind("."):]])
            elif url.path == URLS.api:
                try:
                    self._json(200, api_get(registry, domain))
                except ApiError as exc:
                    self._json(exc.status, {"error": str(exc)})
            elif url.path in ROUTES:
                page = ROUTES[url.path]
                if page == "workspace" and registry.workspace is None:
                    self._send(303, location=URLS.graph)
                elif page != "workspace" and registry.workspace is None and not domain:
                    self._send(303, location=url.path + "?domain=" + quote(next(iter(registry.domains)), safe=""))
                else:
                    html = render_page(page, urls=URLS, token=token, path=url.path,
                                       workspace_enabled=registry.workspace is not None, domains=registry.domains)
                    self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(404, "Nicht gefunden.".encode())

        def do_POST(self) -> None:
            if urlsplit(self.path).path != URLS.api:
                self._json(404, {"error": "Unbekannter Endpunkt."})
                return
            expected_origin = f"http://{self.headers.get('Host', '')}"
            if (not self._valid_host() or self.headers.get("Origin") != expected_origin
                    or not secrets.compare_digest(self.headers.get("X-CSRFToken", ""), token)):
                self._json(403, {"error": "Anfrage nicht für diesen Arbeitsraum freigegeben."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= 1024 * 1024:
                self._json(400, {"error": "Anfrage ist leer oder größer als 1 MiB."})
                return
            try:
                self._json(200, api_post(registry, self.rfile.read(length), self.headers.get_content_type()))
            except ApiError as exc:
                self._json(exc.status, {"error": str(exc)})

    return Handler


def make_server(registry: Registry, host: str = "127.0.0.1", port: int = 8790) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(registry))
