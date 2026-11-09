"""Build the workspace and document domains from one configuration mapping.

The same mapping is used by the slim web app (YAML file) and by Django
(``settings.WISSENSWIKI``)::

    WORKSPACE: ~/dev_wiki                 # optional; None disables the editor
    DOMAINS:                              # optional, read-only sources
      - {name: Dokumentation, source: /repo/doc, relations: ~/dev_wiki_rel}
    MARKDOWN_DATA:                        # optional, scan <root>/<domain>/<subdir>
      {root: ~/dev_data/ki-knowledge, relations: ~/dev_wiki_rel_ki, subdir: md, prefix: "ki:"}
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from wissenswiki_core.discovery import markdown_domains
from wissenswiki_core.domains import DocumentDomain
from wissenswiki_core.workspace import Workspace, WorkspaceError

KEYS = {"WORKSPACE", "DOMAINS", "MARKDOWN_DATA"}


class ConfigError(ValueError):
    """The configuration is incomplete or contradictory."""


@dataclass
class Registry:
    workspace: Workspace | None
    domains: dict[str, DocumentDomain] = field(default_factory=dict)


def _path(value: object, what: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise ConfigError(f"{what} muss ein Pfad sein.")
    return Path(value).expanduser()


def build_registry(config: Mapping) -> Registry:
    if not isinstance(config, Mapping):
        raise ConfigError("Konfiguration muss ein Objekt sein.")
    unknown = set(config) - KEYS
    if unknown:
        raise ConfigError(f"unbekannte Schlüssel {sorted(unknown)}.")
    try:
        workspace_path = config.get("WORKSPACE")
        workspace = Workspace(_path(workspace_path, "WORKSPACE")) if workspace_path else None
        domains: dict[str, DocumentDomain] = {}
        served = [workspace.root] if workspace else []
        for entry in config.get("DOMAINS") or []:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str) or not entry["name"]:
                raise ConfigError("jede Domäne braucht name, source und relations.")
            if entry["name"] in domains:
                raise ConfigError(f"Domäne {entry['name']} doppelt.")
            domain = DocumentDomain(_path(entry.get("source"), "source"), _path(entry.get("relations"), "relations"),
                                    lenient=bool(entry.get("lenient", False)))
            domains[entry["name"]] = domain
            served += [domain.source, domain.storage.root]
        data = config.get("MARKDOWN_DATA")
        if data:
            if not isinstance(data, Mapping):
                raise ConfigError("MARKDOWN_DATA muss ein Objekt sein.")
            root = _path(data.get("root"), "MARKDOWN_DATA.root")
            if not root.is_dir():
                raise ConfigError(f"Datenwurzel existiert nicht: {root}")
            found = markdown_domains(root, _path(data.get("relations"), "MARKDOWN_DATA.relations"),
                                     subdir=data.get("subdir", "md"), prefix=data.get("prefix", ""),
                                     exclude=served)
            for name, source, relations in found:
                if name in domains:
                    raise ConfigError(f"Domäne {name} doppelt.")
                domains[name] = DocumentDomain(source, relations, lenient=bool(data.get("lenient", True)))
    except WorkspaceError as exc:
        raise ConfigError(str(exc)) from exc
    if workspace is None and not domains:
        raise ConfigError("weder WORKSPACE noch Domänen konfiguriert.")
    return Registry(workspace, domains)
