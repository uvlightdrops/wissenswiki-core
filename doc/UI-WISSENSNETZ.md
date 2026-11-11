---
title: "Wissensnetz"
project: wissenswiki-core
agent_project: wissenswiki-core
scope: features
purpose: "Beschreibt die vorhandenen Netz-, Auswahl- und Vergleichsansichten und ihre Verbindung zum UI-Konzept in Next."
created: "2026-11-11 17"
updated: "2026-11-11 20"
update_reason: "Bereinigte Markdown-Inhaltsansichten mit aufklappbarem Quelltext beschrieben"
status: active
relations:
  - target: ../README.md
    type: parent
    reason: Paketübersicht
---

# Wissensnetz

## Erkunden und vergleichen [wissensnetz]

```yaml block-meta
updated: "2026-11-11 20"
status: active
relations:
  - target: ../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#local-workspace
    type: depends-on
    reason: Zusammenwirkende Netz-, Inhalts- und Attributansichten
  - target: ../../ki-knowledge-next/doc/features/ui/INDEX.md#wiki-ui
    type: reference
    reason: Verwendung der gemeinsamen Oberfläche im Next-Host
```

Das SVG-Netz erschließt Blöcke und ihre Beziehungen. Filter, Ausgang/Ziel,
Blockinhalte und Attributvergleich bilden einen gemeinsamen Auswahlkontext.
Die Attributanzeige unterscheidet Blockeigenschaften, Dokumentkontext und
Ablage beziehungsweise Technik; Anzeigeeinstellungen werden teilweise
domänenbezogen im Browser gespeichert.

Die beiden Inhaltsbereiche rendern Markdown einschließlich Listen, Tabellen
und Codeblöcken. Die API liefert dafür neben unverändertem `text` ein
serverseitig bereinigtes `text_html`; aktive HTML-Elemente, Ereignisattribute
und unsichere Linkprotokolle werden entfernt. „Markdown-Quelltext“ zeigt den
Originaltext in einem aufklappbaren Bereich.

Die Sidebar blendet Hinweise auf lediglich fehlende YAML-Header aus.
Ungültige und nicht abgeschlossene Header sowie andere Lesefehler bleiben
sichtbar. Die API behält ihre Fehlerdiagnosen; Einleseregeln werden nicht geändert.

Die Ansichten entsprechen dem Konzept
[Arbeitsraum und Auswahl](../../ki-knowledge-next/doc/architecture/ui/WISSENSWIKI.md#local-workspace).
Sie sind feste, über gemeinsame Blockdaten und konkrete DOM-IDs gekoppelte
Seitenbereiche, keine frei komponierbare Widgetplattform.
HTML, JavaScript und CSS liegen im Core und werden sowohl im Solo-Server
als auch über Framework-Hosts verwendet; es gibt keine zweite Django-Wiki-UI.
