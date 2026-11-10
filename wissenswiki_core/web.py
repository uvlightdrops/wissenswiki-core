"""Slim web app on the standard library ``http.server``.

By default the app is limited to localhost or a trusted LAN. Optional public
access requires an explicit HTTPS origin and HTTP Basic Authentication.
Writes also require the page token and a matching ``Origin``.
"""

from __future__ import annotations

import base64
import binascii
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


class PublicAccessError(ValueError):
    """Public access settings are incomplete or unsafe."""


def _public_origin(value: str) -> tuple[str, str]:
    if any(character.isspace() for character in value):
        raise PublicAccessError("--public-origin darf keine Leerzeichen enthalten.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise PublicAccessError("--public-origin ist ungültig.") from exc
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment or port not in (None, 443)):
        raise PublicAccessError("--public-origin muss eine HTTPS-Origin ohne Pfad oder Nicht-Standardport sein.")
    try:
        hostname = (parsed.hostname if ":" in parsed.hostname
                    else parsed.hostname.encode("idna").decode("ascii")).lower()
    except UnicodeError as exc:
        raise PublicAccessError("--public-origin enthält einen ungültigen Hostnamen.") from exc
    authority = f"[{hostname}]" if ":" in hostname else hostname
    return f"https://{authority}", hostname


def make_handler(registry: Registry, *, public_origin: str | None = None,
                 auth_username: str | None = None,
                 auth_password: str | None = None) -> type[BaseHTTPRequestHandler]:
    normalized_origin = None
    public_hostname = None
    expected_username = auth_username or ""
    expected_password = auth_password or ""
    if public_origin is not None:
        normalized_origin, public_hostname = _public_origin(public_origin)
        if not expected_username or not expected_password:
            raise PublicAccessError(
                "Öffentlicher Zugriff benötigt WISSENSWIKI_AUTH_USERNAME und WISSENSWIKI_AUTH_PASSWORD."
            )
        if ":" in expected_username or "\r" in expected_username or "\n" in expected_username:
            raise PublicAccessError("WISSENSWIKI_AUTH_USERNAME darf keinen Doppelpunkt oder Zeilenumbruch enthalten.")
        if "\r" in expected_password or "\n" in expected_password:
            raise PublicAccessError("WISSENSWIKI_AUTH_PASSWORD darf keinen Zeilenumbruch enthalten.")
    elif auth_username is not None or auth_password is not None:
        raise PublicAccessError("WISSENSWIKI_AUTH_USERNAME/PASSWORD nur zusammen mit --public-origin verwenden.")

    token = secrets.token_hex(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "wissenswiki"

        def _send(self, status: int, body: bytes = b"", content_type: str = "text/plain; charset=utf-8",
                  location: str = "", headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _authorized(self) -> bool:
            if normalized_origin is None:
                return True
            scheme, separator, credentials = self.headers.get("Authorization", "").partition(" ")
            if not separator or scheme.lower() != "basic":
                return False
            try:
                decoded = base64.b64decode(credentials, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                return False
            username, separator, password = decoded.partition(":")
            username_matches = secrets.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8"))
            password_matches = secrets.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
            return bool(separator and username_matches and password_matches)

        def _require_authentication(self) -> bool:
            if self._authorized():
                return True
            self._send(401, b"Authentifizierung erforderlich.\n",
                       headers={"WWW-Authenticate": 'Basic realm="Wissenswiki", charset="UTF-8"'})
            return False

        def _valid_host(self) -> bool:
            try:
                host = self.headers.get("Host", "")
                parsed = urlsplit("http://" + host)
                if (parsed.netloc != host or parsed.path or parsed.query or parsed.fragment
                        or parsed.username or parsed.password):
                    return False
                if public_hostname is not None:
                    return parsed.hostname is not None and parsed.hostname.lower() == public_hostname \
                        and parsed.port in (None, 443)
                if parsed.port != self.server.server_port:
                    return False
                destination = ipaddress.ip_address(self.connection.getsockname()[0])
                if parsed.hostname == "localhost":
                    return destination.is_loopback
                return ipaddress.ip_address(parsed.hostname) == destination
            except ValueError:
                return False

        def do_GET(self) -> None:
            if not self._require_authentication():
                return
            if not self._valid_host():
                message = ("Ungültiger Host; bitte die konfigurierte HTTPS-Origin verwenden."
                           if public_hostname is not None
                           else "Ungültiger Host; bitte die IP-Adresse des Servers verwenden.")
                self._json(403, {"error": message})
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
            if not self._require_authentication():
                return
            if urlsplit(self.path).path != URLS.api:
                self._json(404, {"error": "Unbekannter Endpunkt."})
                return
            expected_origin = normalized_origin or f"http://{self.headers.get('Host', '')}"
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


def make_server(registry: Registry, host: str = "127.0.0.1", port: int = 8790, *,
                public_origin: str | None = None, auth_username: str | None = None,
                auth_password: str | None = None) -> ThreadingHTTPServer:
    handler = make_handler(registry, public_origin=public_origin,
                           auth_username=auth_username, auth_password=auth_password)
    return ThreadingHTTPServer((host, port), handler)
