---
project: wissenswiki-core
scope: Nutzung der schlanken Solo-Web-App
created: null
updated: "2026-11-10 19"
update_reason: Anleitung für Konfiguration und Startskript ergänzt
status: active
agent_project: ki-knowledge
semantic_blocks: [solo-start, wiki-configuration, server-options]
relations:
  - target: ../README.md
    type: reference
    reason: Paketübersicht und Einstieg in die schlanke Web-App
---

# Nutzung

## Solo starten [solo-start]

Das Startskript lädt die lokale `wiki.yaml` aus dem Projektverzeichnis und
startet `wissenswiki serve`. Es verwendet zuerst die Projektumgebung
`.venv`; andernfalls muss der Befehl `wissenswiki` im `PATH` verfügbar sein.

```bash
cp wiki.example.yaml wiki.yaml
# wiki.yaml bei Bedarf bearbeiten
python3 -m pip install -e .
./start.sh
```

Die Beispielkonfiguration startet ein leeres, bearbeitbares Wiki. Die Daten
liegen im Workspace `~/wissenswiki`, nicht im Repository. Die lokale
`wiki.yaml` ist von Git ignoriert.

## Wiki konfigurieren [wiki-configuration]

`WORKSPACE` legt den Ordner für bearbeitbare Wiki-Blöcke fest. Optionale
`DOMAINS` binden bestehende Markdown-Quellen schreibgeschützt ein; `relations`
ist jeweils der zugehörige Ordner für Beziehungsdateien.

```yaml
WORKSPACE: ~/wissenswiki
DOMAINS:
  - name: Dokumentation
    source: ~/projekt/doc
    relations: ~/wissenswiki-relations
```

Weitere optionale Scans lassen sich über `MARKDOWN_DATA` konfigurieren. Die
vollständigen Schlüssel und Validierungsregeln stehen in
`wissenswiki_core/registry.py`.

## Serveroptionen [server-options]

Das Skript akzeptiert dieselben zusätzlichen Serveroptionen wie der CLI-Befehl:

```bash
./start.sh --port 8791
./start.sh --host 0.0.0.0
```

Standardmäßig lauscht die App nur auf `127.0.0.1:8790`. Sie hat keine
Anmeldung; `0.0.0.0` daher nur in einem vertrauten Netzwerk verwenden. Zum
Beenden im Terminal `Ctrl+C` drücken.
