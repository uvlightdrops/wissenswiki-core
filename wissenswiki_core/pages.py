"""HTML pages of the wiki, rendered identically for every web layer."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from string import Template
from urllib.parse import quote

from wissenswiki_core.relations import DEFAULT_CATALOG, RelationDefinition

PAGES = {"workspace": "workspace.html", "graph": "graph.html",
         "graph-header": "graph-header.html", "settings": "settings.html"}


@dataclass(frozen=True)
class PageUrls:
    """Absolute URL paths; ``static`` is the prefix of ``wissenswiki/<asset>`` and ends with ``/``."""

    api: str
    static: str
    workspace: str
    graph: str
    graph_header: str
    settings: str


def render_page(page: str, *, urls: PageUrls, token: str, path: str,
                workspace_enabled: bool, domains: Iterable[str], app_navigation: str = "",
                relation_catalog: tuple[RelationDefinition, ...] = DEFAULT_CATALOG) -> str:
    """Render a page; app_navigation is trusted host-rendered markup, never user input."""
    if page not in PAGES:
        raise ValueError(f"Unbekannte Seite: {page}")
    attr = lambda value: escape(value, quote=True)  # noqa: E731
    nav = (f'<a href="{attr(path)}">Wiki</a> ' if workspace_enabled else "") + " ".join(
        f'<a href="{attr(path + "?domain=" + quote(name, safe=""))}">{escape(name)}</a>' for name in domains)
    enabled = tuple(item for item in relation_catalog if item.enabled)
    relation_label = lambda item: item.label if item.label == item.key else f"{item.label} ({item.key})"
    options = "".join(
        f'<label class="relation-type" title="{attr(item.description)}"><input type="radio" name="relation-type" '
        f'value="{attr(item.key)}"{" checked" if index == 0 else ""}> {escape(relation_label(item))}</label>'
        for index, item in enumerate(enabled))
    workspace_options = "".join(
        f'<option value="{attr(item.key)}" title="{attr(item.description)}">{escape(relation_label(item))}</option>'
        for item in enabled)
    workspace_link = f'<a href="{attr(urls.workspace)}">Arbeitsraum</a> · ' if workspace_enabled else ""
    template = Template(files("wissenswiki_core").joinpath("pages", PAGES[page]).read_text(encoding="utf-8"))
    return template.substitute(
        api=attr(urls.api), static=attr(urls.static + "wissenswiki/"), token=attr(token),
        url_workspace=attr(urls.workspace), url_graph=attr(urls.graph),
        url_graph_header=attr(urls.graph_header), url_settings=attr(urls.settings),
        nav=nav, relation_options=options, workspace_relation_options=workspace_options,
        relation_disabled="" if enabled else " disabled",
        workspace_link=workspace_link, app_navigation=app_navigation)
