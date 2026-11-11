---
title: "Wiki-Arbeitsraum"
project: wissenswiki-core
agent_project: wissenswiki-core
scope: features
purpose: "Beschreibt die vorhandene dateibasierte Blockbearbeitung und verweist auf die UI-Konzepte in Next."
created: "2026-11-11 17"
updated: "2026-11-11 20"
update_reason: "Markdown-Vorschau geordneter Bestandteile beschrieben"
status: active
relations:
  - target: ../README.md
    type: parent
    reason: Paketübersicht
---

# Wiki-Arbeitsraum

## Blöcke bearbeiten und verbinden [arbeitsraum]

```yaml block-meta
updated: "2026-11-11 20"
status: active
relations:
  - target: ../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#local-workspace
    type: depends-on
    reason: Konzept der Bestandsansicht und Zweierauswahl
  - target: ../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#ordered-composition
    type: depends-on
    reason: Konzept geordneter Textteile
  - target: ../../ki-knowledge-next/doc/features/ui/INDEX.md#wiki-ui
    type: reference
    reason: Verwendung der gemeinsamen Oberfläche im Next-Host
```

Ein durchsuchbarer Blockbrowser und zwei Bearbeitungsbereiche ermöglichen
das Öffnen, Gegenüberstellen und Speichern eigener Wiki-Blöcke.
Beziehungen verbinden ausgewählte Blöcke mit Typ und Richtung.
Rechte Blöcke können als geordnete `parts` des linken aufgenommen werden;
eine Vorschau zeigt ihre gespeicherten Texte als bereinigtes Markdown.
Überschriften, Listen, Tabellen und Codeblöcke bleiben strukturiert; aktive
HTML-Inhalte und unsichere Linkziele werden entfernt. Fehlende Bestandteile
bleiben als ausdrücklicher Hinweis sichtbar. Die Textfelder bearbeiten weiterhin
den Markdown-Quelltext.

Dies entspricht den Konzeptblöcken
[Arbeitsraum und Auswahl](../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#local-workspace)
und [Text aus Teilen](../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#ordered-composition).
Die Dateien bleiben der Speicher des Core. Die `parts`-Liste ist keine
Next-Zusammenstellung mit eigenständigen Platzierungen und DB-Revisionsbindung.
