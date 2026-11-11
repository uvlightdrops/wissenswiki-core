---
project: wissenswiki-core
scope: Nutzung der schlanken Solo-Web-App
created: null
updated: "2026-11-10 21"
update_reason: Uberspace-Webbackend-Befehle für U7 und U8 ergänzt
status: active
agent_project: ki-knowledge
semantic_blocks: [solo-start, wiki-configuration, server-options, public-access, uberspace-backend]
relations:
  - target: ../README.md
    type: reference
    reason: Paketübersicht und Einstieg in die schlanke Web-App
  - target: ../../ki-ecosystem/docs/architecture/WEB_HOSTING.md
    type: reference
    reason: Uberspace-Webbackend und Deployment-Konzept
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

Standardmäßig lauscht die App nur auf `127.0.0.1:8790`. `0.0.0.0` ohne
`--public-origin` ist ausschließlich für ein vertrautes LAN gedacht. Zum
Beenden im Terminal `Ctrl+C` drücken.

## Öffentlicher Zugriff [public-access]

Für einen Internetzugriff über Uberspace die öffentliche HTTPS-Origin angeben.
Damit wird HTTP-Basisauthentifizierung für Seiten, API und statische Dateien
aktiviert; ohne beide Zugangsdaten startet dieser Modus nicht. Die Anwendung
bindet dabei standardmäßig an `0.0.0.0`, wie Uberspace-Webbackends es benötigen.
Der Uberspace-Webserver stellt HTTPS bereit und leitet Anfragen an den
konfigurierten Backend-Port weiter. Es ist ein gemeinsames Konto, keine
Benutzerverwaltung; verwende ein langes, nur hierfür genutztes Passwort. Der
Solo-Server begrenzt fehlgeschlagene Anmeldeversuche nicht.

Benutzername und Passwort kommen ausschließlich aus der Prozessumgebung, nicht
aus `wiki.yaml`, der Kommandozeile oder eingecheckten Dateien:

```bash
read -r -p "Wissenswiki-Benutzer: " WISSENSWIKI_AUTH_USERNAME
read -r -s -p "Wissenswiki-Passwort: " WISSENSWIKI_AUTH_PASSWORD; printf '\n'
export WISSENSWIKI_AUTH_USERNAME WISSENSWIKI_AUTH_PASSWORD
./start.sh --port 8790 --public-origin https://wiki.example.org
```

Für einen dauerhaften Uberspace-Dienst müssen dieselben Variablen in dessen
Prozessumgebung gesetzt sein. `--public-origin` muss genau der von außen
verwendeten HTTPS-Origin entsprechen; der Host-Header und Schreibzugriffe
werden dagegen geprüft. Der Browser fragt nach HTTP-Basisauthentifizierung.
Uberspace-Backend-Zuordnung und Prozessverwaltung gehören zum
[Ecosystem-Deployment-Konzept](../../ki-ecosystem/docs/architecture/WEB_HOSTING.md).

Das Solo-Wiki liefert derzeit Routen ab der Domainwurzel aus und ist nicht für
einen Unterpfad wie `/wiki/` angepasst. Dafür eine eigene Domain/Subdomain
verwenden oder zuerst die Unterstützung für einen Basispfad ergänzen.

## Uberspace-Webbackend einrichten [uberspace-backend]

Die Domain oder Subdomain muss bereits für den Uberspace eingerichtet sein.
Das Wiki muss als dauerhafter Dienst auf Port `8790` laufen und mit
`--public-origin https://wiki.example.org` sowie den beiden
Authentifizierungsvariablen gestartet sein. Der öffentliche Modus bindet an
`0.0.0.0`; Uberspace-Webbackends benötigen eine öffentliche Bind-Adresse und
einen Port zwischen `1024` und `65535`.

Eine eigene Subdomain verwenden, damit die bestehende Hauptdomain und deren
Root-Backend unberührt bleiben. `wiki.example.org` in den Befehlen durch die
konfigurierte Domain ersetzen.

**Uberspace 7:**

```bash
uberspace web backend set wiki.example.org/ --http --port 8790
uberspace web backend list
```

**Uberspace 8:**

```bash
uberspace web backend add wiki.example.org/ port 8790
uberspace web backend list
```

Die Liste sollte die Domain mit Ziel `8790` anzeigen. Zum Entfernen des
Backends:

```bash
# Uberspace 7 und 8
uberspace web backend del wiki.example.org/
```

Die Backend-Befehle richten nur die Weiterleitung ein; sie starten oder
überwachen den Wiki-Prozess nicht. Dafür den passenden Supervisor- (U7) oder
systemd-User-Dienst (U8) verwenden und sicherstellen, dass dieser die
Auth-Variablen erhält. Siehe die
[Uberspace-7-Anleitung](https://manual.uberspace.de/web-backends/) und die
[Uberspace-8-Anleitung](https://u8manual.uberspace.de/web_backends/).
