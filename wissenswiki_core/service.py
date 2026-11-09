"""Framework-neutral JSON API shared by the slim web app and Django."""

from __future__ import annotations

import json

from wissenswiki_core.registry import Registry
from wissenswiki_core.workspace import WorkspaceConflict, WorkspaceError

MAX_BODY = 1024 * 1024


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def api_get(registry: Registry, domain: str = "") -> dict:
    try:
        if domain:
            if domain not in registry.domains:
                raise WorkspaceError("Unbekannte Domäne.")
            return registry.domains[domain].snapshot()
        if registry.workspace is None:
            raise WorkspaceError("Bitte eine Domäne auswählen.")
        return {"blocks": registry.workspace.list_blocks(), "errors": []}
    except WorkspaceError as exc:
        raise ApiError(400, str(exc)) from exc


def api_post(registry: Registry, body: bytes, content_type: str) -> dict:
    if content_type != "application/json":
        raise ApiError(415, "JSON wird erwartet.")
    try:
        if not 0 < len(body) <= MAX_BODY:
            raise WorkspaceError("Anfrage ist leer oder größer als 1 MiB.")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise WorkspaceError("JSON-Objekt wird erwartet.")
        action, name = payload.get("action"), payload.get("domain", "")
        if name:
            if not isinstance(name, str) or name not in registry.domains or action != "graph-relate":
                raise WorkspaceError("Unbekannte Domäne oder Aktion.")
            return registry.domains[name].relate(payload)
        if registry.workspace is None:
            raise WorkspaceError("Bitte eine Domäne auswählen.")
        if action == "create":
            return registry.workspace.create(payload.get("title"), payload.get("text"))
        return registry.workspace.update(payload.get("id"), payload.get("revision"), action, payload)
    except WorkspaceConflict as exc:
        raise ApiError(409, str(exc)) from exc
    except (WorkspaceError, ValueError, UnicodeError) as exc:
        raise ApiError(400, str(exc)) from exc
