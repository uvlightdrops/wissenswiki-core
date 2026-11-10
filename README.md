---
project: wissenswiki-core
scope: Überblick, schlanke Web-App und Einbindung des Kerns
created: null
updated: "2026-11-09 11"
update_reason: Erste Fassung
status: active
agent_project: ki-knowledge
---

# wissenswiki-core

Wissensblöcke aus Markdown-Dateien mit typisierten Beziehungen und SVG-Wissensnetz.
Das Paket braucht nur die Standardbibliothek und PyYAML.
Es bringt eine schlanke Web-App mit; Framework-Schichten wie `wissenswiki-django` bauen darauf auf.

## Aufbau [package-layout]

| Modul | Zweck |
|-------|-------|
| `documents`, `relations`, `workspace`, `domains`, `discovery` | Blöcke, Beziehungen, Arbeitsraum, Domänen |
| `registry` | Baut Arbeitsraum und Domänen aus einer Konfiguration; Fehler als `ConfigError` |
| `service` | JSON-API (`api_get`, `api_post`), unabhängig vom Webframework |
| `pages`, `pages/*.html`, `static/wissenswiki/` | Oberfläche; einmal vorhanden, von allen Web-Schichten genutzt |
| `web`, `cli` | Schlanke Web-App auf `http.server`, Befehl `wissenswiki serve` |

Die Dateien bleiben die Quelle der Wahrheit; es gibt keine Datenbank.

## Schlanke Web-App [slim-web-app]

```bash
pip install -e .
wissenswiki serve --workspace ~/dev_wiki \
  --domain Dokumentation ~/dev_flow/ki-knowledge/doc ~/dev_wiki_rel
wissenswiki serve --config wiki.yaml --port 8790   # alternativ
```

Für den Solo-Betrieb mit Startskript siehe [Nutzung](doc/USAGE.md).
Eine Beispielkonfiguration liegt in `wiki.example.yaml`.

Die YAML-Datei nutzt dieselben Schlüssel wie `settings.WISSENSWIKI` in Django: `WORKSPACE`, `DOMAINS` und `MARKDOWN_DATA`.
Das Schema steht in `wissenswiki_core/registry.py`.

Die App ist für eine Person auf `localhost` oder im vertrauten LAN gedacht und hat keine Anmeldung.
Schutz bieten eine strenge CSP, die Host-Prüfung über die numerische Adresse sowie für Schreibzugriffe Seiten-Token und `Origin`.
Für das LAN mit `--host 0.0.0.0` starten und die Seite über die IP-Adresse aufrufen.

## Tests [tests]

```bash
pip install -e '.[test]'
python -m pytest -q
```
