---
project: wissenswiki-core
scope: Überblick, schlanke Web-App und Einbindung des Kerns
created: null
updated: "2026-11-11 19"
update_reason: Konfigurierbaren Betreiberkatalog und gemeinsame API-Validierung dokumentiert
status: active
agent_project: ki-knowledge
semantic_blocks: [package-layout, slim-web-app, relation-catalog, tests]
relations:
  - target: doc/UI-ARBEITSRAUM.md
    type: child
    reason: Dateibasierte Blockbearbeitung und geordnete Teile
  - target: doc/UI-WISSENSNETZ.md
    type: child
    reason: Exploration und Vergleich in der gemeinsamen Oberfläche
  - target: doc/USAGE.md
    type: reference
    reason: Anleitung zum Starten der Solo-Web-App
---

# wissenswiki-core

Wissensblöcke aus Markdown-Dateien mit typisierten Beziehungen und SVG-Wissensnetz.
Das Paket nutzt die Standardbibliothek sowie PyYAML, Markdown und bleach.
Es bringt eine schlanke Web-App mit; Framework-Schichten wie `wissenswiki-django` bauen darauf auf.

Die vorhandene UI ist unter [Arbeitsraum](doc/UI-ARBEITSRAUM.md) und
[Wissensnetz](doc/UI-WISSENSNETZ.md) beschrieben; beide verweisen auf die
zugehörigen Konzepte in `ki-knowledge-next`.

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

```yaml block-meta
updated: "2026-11-11 19"
status: active
relations: []
```

```bash
pip install -e .
wissenswiki serve --workspace ~/dev_wiki \
  --domain Dokumentation ~/dev_flow/ki-knowledge/doc ~/dev_wiki_rel
wissenswiki serve --config wiki.yaml --port 8790   # alternativ
```

Für den Solo-Betrieb mit Startskript siehe [Nutzung](doc/USAGE.md).
Eine Beispielkonfiguration liegt in `wiki.example.yaml`.

Die YAML-Datei nutzt dieselben Schlüssel wie `settings.WISSENSWIKI` in Django:
`WORKSPACE`, `DOMAINS`, `MARKDOWN_DATA` und `RELATION_CATALOG`.
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

## Beziehungskatalog [relation-catalog]

```yaml block-meta
updated: "2026-11-11 19"
status: active
relations:
  - target: ../wissenswiki-django/README.md#integration
    type: reference
    reason: Django übernimmt dieselbe Betreiberkonfiguration und Oberfläche
```

`RELATION_CATALOG` gilt gemeinsam für Arbeitsraum, Dokumentdomänen und
Wissensnetz. Ohne Eintrag ist `documentation` aktiv. `basic` enthält
`reference`, `part-of`, `composed-of`, `depends-on`; `documentation` ergänzt
`implements`, `extends`, `references`, `deprecates`, `parent`, `child` und
erhält damit alle sieben bisherigen Typen. `knowledge` ergänzt `supports`,
`contradicts`, `questions` mit gerichteten Beschreibungen.

```yaml
RELATION_CATALOG:
  preset: documentation
  types:
    - key: informs
      label: Informiert
      description: Der Ausgang informiert das Ziel.
      color: "#527a92"    # optional, Standard gray
      enabled: true     # optional, Standard true
```

Jeder eigene Typ benötigt `key`, `label` und `description`. Schlüssel sind
kleingeschriebene Slugs (Buchstabe am Anfang, höchstens 80 Zeichen), Texte
dürfen nicht leer sein. Farben sind CSS-Namen ohne Sonderzeichen oder
Hexfarben (`#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`). Doppelte Schlüssel, unbekannte
Felder/Presets und ungültige Werte führen zu `ValueError`, beim Registry-Aufbau
zu `ConfigError`. Preset-Schlüssel dürfen Label, Farbe und Aktivierung
überschreiben, aber nur mit ihrer exakt unveränderten `description`.
`reference` und `references` bleiben verschiedene Schlüssel; es gibt keine
automatische Umschreibung.

`wissenswiki_core.relations.build_catalog(config=None)` liefert ein Tupel
unveränderlicher `RelationDefinition`-Objekte mit `key`, `label`,
`description`, `color`, `enabled` und `as_dict()`. `Registry.relation_catalog`
und die optionalen Konstruktorparameter `Workspace(..., relation_catalog=...)`
und `DocumentDomain(..., relation_catalog=...)` verwenden diesen Katalog.
`RELATION_TYPES` bleibt das kompatible Tupel `(key, color)` des aktivierten
Standardkatalogs. `render_page(..., relation_catalog=...)` rendert alle
aktivierten Typen mit Label/Schlüssel und Beschreibung als Tooltip.

GET `/api` beziehungsweise `/api?domain=...` liefert zusätzlich
`relation_types` mit **allen** fünf Definitionsfeldern, auch deaktivierten
Typen. `blocks`, `errors` und die Domänen-`revision` bleiben erhalten.
Beide Schreibaktionen `relate` und `graph-relate` akzeptieren nur aktivierte
Katalogschlüssel; der Arbeitsraum bietet dafür eine Auswahl statt Freitext.
Gespeicherte Beziehungen bleiben auch nach Presetwechsel unverändert lesbar,
bearbeitbare Blocktexte behalten sie. Im Netz erhalten verwendete deaktivierte
oder unbekannte Typen nur lesbare Legendeneinträge; der Filter enthält weiterhin
alle verwendeten Typen. Ohne aktivierte Typen ist das Verbinden deaktiviert.

## Tests [tests]

```yaml block-meta
updated: "2026-11-11 19"
status: active
relations: []
```

```bash
pip install -e '.[test]'
python -m pytest -q
node --test tests/attribute-settings.test.js tests/relation-catalog.test.js
```

Die JavaScript-Tests benötigen Node.js, aber keine zusätzlichen npm-Pakete.
