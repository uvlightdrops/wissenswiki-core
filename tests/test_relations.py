from dataclasses import FrozenInstanceError
import http.client
import json
import threading

import pytest

from wissenswiki_core.pages import PageUrls, render_page
from wissenswiki_core.registry import ConfigError, build_registry
from wissenswiki_core.relations import DEFAULT_CATALOG, RELATION_TYPES, build_catalog
from wissenswiki_core.service import ApiError, api_get, api_post
from wissenswiki_core.workspace import Workspace, WorkspaceError
from wissenswiki_core.web import make_server


def test_presets_are_frozen_directional_and_preserve_distinct_keys():
    basic = build_catalog({"preset": "basic"})
    assert [item.key for item in basic] == ["reference", "part-of", "composed-of", "depends-on"]
    assert set(dict(RELATION_TYPES)) == {
        "reference", "depends-on", "part-of", "composed-of", "implements", "extends",
        "references", "deprecates", "parent", "child",
    }
    knowledge = build_catalog({"preset": "knowledge"})
    assert {item.key for item in knowledge} - set(dict(RELATION_TYPES)) == {"supports", "contradicts", "questions"}
    assert all("Ausgang" in item.description and "Ziel" in item.description for item in knowledge[-3:])
    assert basic[0].description == (
        "Verweist auf eine verwandte Ressource, ohne Zustimmung, Reihenfolge oder Abhängigkeit zu behaupten.")
    assert build_catalog() == DEFAULT_CATALOG
    assert set(basic[0].as_dict()) == {"key", "label", "description", "color", "enabled"}
    with pytest.raises(FrozenInstanceError):
        basic[0].enabled = False


def test_custom_types_and_presentation_overrides_keep_preset_meaning():
    preset = DEFAULT_CATALOG[0]
    catalog = build_catalog({"types": [
        {**preset.as_dict(), "label": "Benötigt", "color": "#123abc", "enabled": False},
        {"key": "informs", "label": "Informiert", "description": "Der Ausgang informiert das Ziel."},
    ]})
    assert catalog[0].description == preset.description
    assert catalog[0].label == "Benötigt" and catalog[0].enabled is False
    assert catalog[-1].color == "gray" and catalog[-1].enabled is True
    assert "depends-on" in dict(RELATION_TYPES)
    override = build_catalog({"types": [
        {"key": preset.key, "label": "Benötigt", "description": preset.description}]})
    assert override[0].color == "gray" and override[0].enabled is True


@pytest.mark.parametrize("config", [
    [], {"preset": "unknown"}, {"preset": []}, {"unknown": 1}, {"types": None},
    {"types": [{}]}, {"types": [False]},
    {"types": [{"key": "bad key", "label": "X", "description": "Y"}]},
    {"types": [{"key": "x" * 81, "label": "X", "description": "Y"}]},
    {"types": [{"key": "x", "label": " ", "description": "Y"}]},
    {"types": [{"key": "x", "label": "X", "description": "\n"}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "color": "red;display:none"}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "color": "url(https://x)"}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "color": "#12345"}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "color": "notacolor"}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "enabled": 1}]},
    {"types": [{"key": "x", "label": "X", "description": "Y", "extra": True}]},
    {"types": [{"key": "x", "label": "X", "description": "Y"}] * 2},
    {"types": [{"key": "reference", "label": "X", "description": "Different meaning"}]},
    {"preset": "basic", "types": [{"key": "supports", "label": "X", "description": "Different meaning"}]},
])
def test_invalid_catalog_fails_explicitly_and_registry_wraps_error(config):
    with pytest.raises(ValueError):
        build_catalog(config)
    with pytest.raises(ConfigError):
        build_registry({"RELATION_CATALOG": config})


@pytest.mark.parametrize("action", ["relate", "graph-relate"])
def test_workspace_uses_effective_catalog_and_keeps_disabled_edges_readable(tmp_path, action):
    workspace = Workspace(tmp_path)
    first, second = workspace.create("A", ""), workspace.create("B", "")
    first = workspace.update(first["id"], first["revision"], action,
                             {"target": second["id"], "type": "extends"})
    before = (tmp_path / f'{first["id"]}.md').read_bytes()
    custom = {"key": "informs", "label": "Informiert", "description": "Der Ausgang informiert das Ziel."}
    switched = Workspace(tmp_path, relation_catalog=build_catalog({"preset": "basic", "types": [custom]}))
    reopened = {item["id"]: item for item in switched.list_blocks()}
    assert reopened[first["id"]]["relations"] == [{"target": second["id"], "type": "extends"}]
    assert (tmp_path / f'{first["id"]}.md').read_bytes() == before
    for kind in ("extends", "arbitrary", " reference "):
        with pytest.raises(WorkspaceError, match="Beziehungstyp"):
            switched.update(first["id"], first["revision"], action, {"target": second["id"], "type": kind})
    first = switched.update(first["id"], first["revision"], action, {"target": second["id"], "type": "informs"})
    assert first["relations"] == [
        {"target": second["id"], "type": "extends"}, {"target": second["id"], "type": "informs"}]
    saved = switched.update(first["id"], first["revision"], "save", {"title": "A edited", "text": ""})
    assert saved["relations"] == first["relations"]


@pytest.mark.parametrize("action", ["relate", "graph-relate"])
def test_workspace_rejects_disabled_configured_type_for_both_actions(tmp_path, action):
    catalog = build_catalog({"types": [{**DEFAULT_CATALOG[0].as_dict(), "enabled": False}]})
    workspace = Workspace(tmp_path, relation_catalog=catalog)
    first, second = workspace.create("A", ""), workspace.create("B", "")
    with pytest.raises(WorkspaceError, match="deaktivierter"):
        workspace.update(first["id"], first["revision"], action,
                         {"target": second["id"], "type": DEFAULT_CATALOG[0].key})


def test_registry_propagates_catalog_to_all_domains_and_api_preserves_errors(tmp_path):
    for name in ("workspace", "docs", "relations", "data", "data-rel"):
        (tmp_path / name).mkdir()
    md = tmp_path / "data" / "book" / "md"
    md.mkdir(parents=True)
    (md / "plain.md").write_text("# Plain")
    (tmp_path / "docs" / "a.md").write_text("---\n{}\n---\n# A\n## One [one]\n## Two [two]\n")
    (tmp_path / "docs" / "bad.md").write_text("No header")
    config = {"WORKSPACE": tmp_path / "workspace",
              "DOMAINS": [{"name": "Docs", "source": tmp_path / "docs", "relations": tmp_path / "relations"}],
              "MARKDOWN_DATA": {"root": tmp_path / "data", "relations": tmp_path / "data-rel"}}
    registry = build_registry(config)
    domain = registry.domains["Docs"]
    updated = domain.relate({"id": "doc:a.md#one", "target": "doc:a.md#two",
                             "type": "references", "revision": domain.snapshot()["revision"]})
    stored = (tmp_path / "relations" / "dokument-beziehungen.json").read_bytes()
    config["RELATION_CATALOG"] = {"preset": "basic"}
    registry = build_registry(config)
    assert registry.workspace.relation_catalog is registry.relation_catalog
    assert all(item.relation_catalog is registry.relation_catalog for item in registry.domains.values())
    snapshot = api_get(registry, "Docs")
    assert snapshot["errors"] and snapshot["revision"] == updated["revision"]
    assert snapshot["blocks"][1]["relations"] == [{"target": "doc:a.md#two", "type": "references"}]
    assert snapshot["relation_types"] == api_get(registry)["relation_types"]
    payload = {"action": "graph-relate", "domain": "Docs", "id": "doc:a.md#one",
               "target": "doc:a.md#two", "type": "references", "revision": snapshot["revision"]}
    with pytest.raises(ApiError, match="Beziehungstyp"):
        api_post(registry, json.dumps(payload).encode(), "application/json")
    assert (tmp_path / "relations" / "dokument-beziehungen.json").read_bytes() == stored
    payload["type"] = "reference"
    api_post(registry, json.dumps(payload).encode(), "application/json")


@pytest.mark.parametrize("page", ["workspace", "graph", "graph-header"])
def test_rendering_has_all_enabled_choices_not_just_used_types_and_escapes_text(page):
    urls = PageUrls("/api", "/static/", "/", "/graph", "/header", "/settings")
    catalog = build_catalog({"types": [
        {**DEFAULT_CATALOG[0].as_dict(), "enabled": False},
        {"key": "new-type", "label": "<Title>", "description": '"Direction"', "color": "#abc"},
    ]})
    html = render_page(page, urls=urls, token="t", path="/", workspace_enabled=True,
                       domains=[], relation_catalog=catalog)
    assert 'value="new-type"' in html and "&lt;Title&gt; (new-type)" in html
    assert 'title="&quot;Direction&quot;"' in html and 'style=' not in html
    assert 'value="depends-on"' not in html
    assert all(f'value="{item.key}"' in html for item in catalog if item.enabled)
    if page == "workspace":
        assert '<select id="type"' in html and "<datalist" not in html
    empty = render_page(page, urls=urls, token="t", path="/", workspace_enabled=True,
                        domains=[], relation_catalog=())
    assert ('id="relate" disabled' if page == "workspace" else 'id="connect" type="button" disabled') in empty


def test_solo_server_passes_current_catalog_to_pages_and_api(tmp_path):
    registry = build_registry({"WORKSPACE": tmp_path, "RELATION_CATALOG": {"preset": "basic", "types": [
        {"key": "informs", "label": "Informiert", "description": "Der Ausgang informiert das Ziel.", "color": "#abcd"},
    ]}})
    server = make_server(registry, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(*server.server_address)
    try:
        for path in ("/", "/graph/", "/graph-header/", "/api"):
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read().decode()
            assert response.status == 200
            if path == "/api":
                assert json.loads(body)["relation_types"] == [item.as_dict() for item in registry.relation_catalog]
            else:
                assert 'value="informs"' in body and 'value="references"' not in body
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join()
