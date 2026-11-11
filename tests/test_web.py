import base64
import http.client
import json
import re
import subprocess
import sys
import threading

import pytest

from wissenswiki_core.cli import main
from wissenswiki_core.pages import PageUrls, render_page
from wissenswiki_core.registry import ConfigError, build_registry
from wissenswiki_core.web import make_server


@pytest.fixture
def server(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "ws").mkdir()
    (tmp_path / "rel").mkdir()
    (tmp_path / "docs" / "a.md").write_text("---\n{}\n---\n# A\n## Eins [eins]\nText\n")
    registry = build_registry({"WORKSPACE": str(tmp_path / "ws"), "DOMAINS": [
        {"name": "Doku", "source": str(tmp_path / "docs"), "relations": str(tmp_path / "rel")}]})
    httpd = make_server(registry, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def public_server(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "ws").mkdir()
    (tmp_path / "rel").mkdir()
    (tmp_path / "docs" / "a.md").write_text("---\n{}\n---\n# A\n## Eins [eins]\nText\n")
    registry = build_registry({"WORKSPACE": str(tmp_path / "ws"), "DOMAINS": [
        {"name": "Doku", "source": str(tmp_path / "docs"), "relations": str(tmp_path / "rel")}]})
    httpd = make_server(registry, port=0, public_origin="https://wiki.example",
                        auth_username="álîçé", auth_password="sëcret")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def request(port, method, path, body=None, headers=None, host=None):
    connection = http.client.HTTPConnection("127.0.0.1", port)
    connection.request(method, path, body=body, headers={"Host": host or f"127.0.0.1:{port}", **(headers or {})})
    response = connection.getresponse()
    return response.status, dict(response.getheaders()), response.read().decode()


def basic_auth(username="álîçé", password="sëcret"):
    value = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {value}"}


def test_pages_static_and_domain_api(server):
    status, _, workspace = request(server, "GET", "/")
    assert status == 200 and '<a href="/graph-header/">Wissensnetz öffnen</a>' in workspace
    status, headers, page = request(server, "GET", "/graph-header/?domain=Doku")
    assert status == 200 and "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert 'href="/settings/"' in page and '/graph-header/?domain=Doku' in page and "${" not in page
    status, _, settings_page = request(server, "GET", "/settings/?domain=Doku")
    assert status == 200 and 'id="graph-height"' in settings_page and 'type="range"' in settings_page
    assert 'id="attribute-preset"' not in settings_page
    assert all(f'id="show-{preset}"' in settings_page for preset in ("block", "all", "none"))
    assert 'id="attribute-selection"' in settings_page
    assert "Dokumentkontext" in settings_page
    assert request(server, "GET", "/static/wissenswiki/graph.js")[0] == 200
    assert request(server, "GET", "/static/wissenswiki/markdown.css")[0] == 200
    assert 'href="/static/wissenswiki/markdown.css"' in page
    assert request(server, "GET", "/static/wissenswiki/../pages/graph.html")[0] == 404
    status, _, body = request(server, "GET", "/api?domain=Doku")
    assert status == 200 and json.loads(body)["blocks"]
    assert request(server, "GET", "/", host="evil.example")[0] == 403


def test_public_access_requires_basic_auth_and_configured_host(public_server):
    status, headers, _ = request(public_server, "GET", "/", host="wiki.example")
    assert status == 401
    assert headers["WWW-Authenticate"].startswith("Basic realm=")
    assert request(public_server, "GET", "/", headers={"Authorization": "Basic !!!"},
                   host="wiki.example")[0] == 401
    assert request(public_server, "GET", "/", headers=basic_auth("álîçé", "wrong"),
                   host="wiki.example")[0] == 401
    assert request(public_server, "GET", "/static/wissenswiki/graph.js",
                   host="wiki.example")[0] == 401
    assert request(public_server, "GET", "/", headers=basic_auth(), host="evil.example")[0] == 403
    status, _, page = request(public_server, "GET", "/", headers=basic_auth(), host="wiki.example")
    assert status == 200 and 'name="workspace-token"' in page


def test_public_writes_require_authenticated_https_origin(public_server):
    auth = basic_auth()
    _, _, page = request(public_server, "GET", "/", headers=auth, host="wiki.example")
    token = re.search(r'name="workspace-token" content="(\w+)"', page).group(1)
    body = json.dumps({"action": "create", "title": "Essay", "text": "Inhalt"})
    headers = {"Content-Type": "application/json", "Origin": "https://wiki.example",
               "X-CSRFToken": token, **auth}
    status, _, created = request(public_server, "POST", "/api", body, headers, host="wiki.example")
    assert status == 200 and json.loads(created)["title"] == "Essay"
    assert request(public_server, "POST", "/api", body,
                   {key: value for key, value in headers.items() if key != "Authorization"},
                   host="wiki.example")[0] == 401
    assert request(public_server, "POST", "/api", body, {**headers, "Origin": "http://wiki.example"},
                   host="wiki.example")[0] == 403


def test_writes_need_token_and_origin(server):
    token = re.search(r'name="workspace-token" content="(\w+)"', request(server, "GET", "/")[2]).group(1)
    origin = f"http://127.0.0.1:{server}"
    body = json.dumps({"action": "create", "title": "Essay", "text": "Inhalt"})
    json_type = {"Content-Type": "application/json", "Origin": origin}
    assert request(server, "POST", "/api", body, json_type)[0] == 403
    status, _, created = request(server, "POST", "/api", body, {**json_type, "X-CSRFToken": token})
    assert status == 200 and json.loads(created)["title"] == "Essay"
    assert request(server, "POST", "/api", body, {**json_type, "X-CSRFToken": token, "Origin": "http://x"})[0] == 403
    status, _, error = request(server, "POST", "/api", "x", {"Content-Type": "text/plain", "Origin": origin,
                                                              "X-CSRFToken": token})
    assert status == 415 and "JSON" in error


def test_configuration_errors_are_reported(tmp_path, capsys):
    with pytest.raises(ConfigError, match="unbekannte"):
        build_registry({"WORKSPAC": "x"})
    with pytest.raises(ConfigError, match="weder"):
        build_registry({})
    with pytest.raises(SystemExit):
        main(["serve", "--config", str(tmp_path / "fehlt.yaml")])
    assert "nicht lesbar" in capsys.readouterr().err


def test_public_access_requires_https_origin_and_both_credentials(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("WISSENSWIKI_AUTH_USERNAME", "wiki-user")
    monkeypatch.delenv("WISSENSWIKI_AUTH_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        main(["serve", "--workspace", str(workspace), "--public-origin", "https://wiki.example"])
    assert "WISSENSWIKI_AUTH_USERNAME" in capsys.readouterr().err
    registry = build_registry({"WORKSPACE": str(workspace)})
    with pytest.raises(ValueError, match="HTTPS-Origin"):
        make_server(registry, public_origin="http://wiki.example",
                    auth_username="alice", auth_password="secret")


def test_public_cli_defaults_to_public_interface_and_prints_origin(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("WISSENSWIKI_AUTH_USERNAME", "wiki-user")
    monkeypatch.setenv("WISSENSWIKI_AUTH_PASSWORD", "private-password")
    observed = {}

    class FakeServer:
        server_address = ("0.0.0.0", 8790)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    def fake_make_server(registry, host, port, **options):
        observed.update(host=host, port=port, **options)
        return FakeServer()

    monkeypatch.setattr("wissenswiki_core.cli.make_server", fake_make_server)
    main(["serve", "--workspace", str(workspace), "--public-origin", "https://wiki.example"])

    assert observed == {
        "host": "0.0.0.0", "port": 8790, "public_origin": "https://wiki.example",
        "auth_username": "wiki-user", "auth_password": "private-password",
    }
    assert capsys.readouterr().out == "Wissenswiki: https://wiki.example/\n"


def test_pages_escape_domain_names():
    urls = PageUrls("/api", "/s/", "/", "/g/", "/gh/", "/st/")
    page = render_page("graph", urls=urls, token="t", path="/g/", workspace_enabled=False, domains=['<b>"x'])
    assert "&lt;b&gt;&quot;x" in page and "<b>" not in page
    with pytest.raises(ValueError):
        render_page("nope", urls=urls, token="t", path="/", workspace_enabled=False, domains=[])


@pytest.mark.parametrize("view", ["graph", "graph-header"])
def test_graph_pages_include_block_content_widget(view):
    urls = PageUrls("/api", "/s/", "/", "/g/", "/gh/", "/st/")
    page = render_page(view, urls=urls, token="t", path="/g/", workspace_enabled=True, domains=[])
    assert '<summary>Blockinhalt</summary>' in page
    assert 'id="block-content"' in page
    assert 'aria-label="Inhalt von Ausgang und Ziel"' in page


@pytest.mark.parametrize("view", ["graph", "graph-header"])
def test_graph_pages_relation_type_widget_is_collapsed_by_default(view):
    urls = PageUrls("/api", "/s/", "/", "/g/", "/gh/", "/st/")
    page = render_page(view, urls=urls, token="t", path="/g/", workspace_enabled=True, domains=[])
    assert '<details class="relation-widget"><summary>Beziehungen</summary>' in page
    assert '<fieldset class="legend"><legend>Farben und Richtung</legend>' in page


@pytest.mark.parametrize("view", ["graph", "graph-header"])
def test_graph_pages_default_bubble_color_to_folder(view):
    urls = PageUrls("/api", "/s/", "/", "/g/", "/gh/", "/st/")

    page = render_page(view, urls=urls, token="t", path="/g/", workspace_enabled=True, domains=[])

    assert '<option value="folder" selected>Nach Ordner</option>' in page
    assert '<option value="uniform">Einheitlich</option>' in page


@pytest.mark.parametrize("view", ["workspace", "graph", "graph-header", "settings"])
def test_pages_accept_optional_trusted_host_navigation(view):
    urls = PageUrls("/api", "/s/", "/", "/g/", "/gh/", "/st/")
    arguments = dict(urls=urls, token="t", path="/g/", workspace_enabled=True, domains=[])
    assert "${" not in render_page(view, **arguments)
    navigation = '<nav aria-label="Host">Application</nav>'
    assert render_page(view, app_navigation=navigation, **arguments).count(navigation) == 1


def test_core_imports_no_framework():
    code = ("import sys, wissenswiki_core.web, wissenswiki_core.cli, wissenswiki_core.domains;"
            "print(any(m.split('.')[0] in {'django', 'flask'} for m in sys.modules))")
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip() == "False"
