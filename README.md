---
project: wissenswiki-core
scope: Überblick, schlanke Web-App und Einbindung des Kerns
created: null
updated: "2026-11-10 20"
update_reason: Abgesicherten öffentlichen Zugriff für Uberspace dokumentiert
status: active
agent_project: ki-knowledge
semantic_blocks: [package-layout, slim-web-app, tests]
relations:
  - target: doc/USAGE.md
    type: reference
    reason: Anleitung zum Starten der Solo-Web-App
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

Standardmäßig ist die App für eine Person auf `localhost` oder im vertrauten LAN
gedacht und hat keine Anmeldung. Öffentlicher Zugriff ist nur im expliziten
Modus mit HTTPS-Origin und HTTP-Basisauthentifizierung vorgesehen; Details in
der [Nutzungsanleitung](doc/USAGE.md).
Schutz bieten außerdem eine strenge CSP, Host-Prüfung sowie für Schreibzugriffe
Seiten-Token und `Origin`.

Die Einstellungen bieten „Nur Blockattribute“ (Standard), „Alle Attribute“
und „Keine“ als direkte Buttons. Einzelne Checkboxen bleiben frei schaltbar;
die aktuelle eigene Auswahl wird als „Benutzerdefiniert“ angezeigt und pro
Domäne im Browser gespeichert. Die Anzeige trennt
Eigenschaften der Auswahl, Dokumentkontext und Ablage/Technik. Dokument-Metadaten
aus `dokument_metadaten` sind Kontext; `metadaten` eigener Wiki-Blöcke gehören
zum Block. Einzelne Attribute werden über ihren vollständigen Pfad ausgewählt,
ohne Suche und Filter zu verändern. Bisherige gespeicherte Kurznamenauswahlen
bleiben wirksam; beim Bearbeiten werden sie für die vorhandenen Attribute
in vollständige Pfade überführt.

## Tests [tests]

```bash
pip install -e '.[test]'
python -m pytest -q
node --test tests/attribute-settings.test.js
```

Die JavaScript-Tests benötigen Node.js, aber keine zusätzlichen npm-Pakete.
