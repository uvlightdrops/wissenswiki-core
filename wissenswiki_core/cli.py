"""Command line: ``wissenswiki serve``."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from wissenswiki_core.registry import ConfigError, build_registry
from wissenswiki_core.web import make_server


def _config(args: argparse.Namespace) -> dict:
    if args.config and (args.workspace or args.domain):
        raise ConfigError("--config nicht zusammen mit --workspace/--domain verwenden.")
    if args.config:
        try:
            return yaml.safe_load(Path(args.config).expanduser().read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"Konfiguration nicht lesbar: {exc}") from exc
    return {"WORKSPACE": args.workspace,
            "DOMAINS": [{"name": n, "source": s, "relations": r} for n, s, r in args.domain or []]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wissenswiki")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Schlanke Web-App starten")
    serve.add_argument("--config", help="YAML-Datei mit WORKSPACE, DOMAINS, MARKDOWN_DATA")
    serve.add_argument("--workspace", help="Ordner für bearbeitbare Blöcke")
    serve.add_argument("--domain", nargs=3, action="append", metavar=("NAME", "QUELLE", "BEZIEHUNGEN"),
                       help="Markdown-Ordner nur lesend einbinden (mehrfach möglich)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8790)
    args = parser.parse_args(argv)
    try:
        registry = build_registry(_config(args))
    except ConfigError as exc:
        parser.error(str(exc))
    server = make_server(registry, args.host, args.port)
    host, port = server.server_address[:2]
    print(f"Wissenswiki: http://{'localhost' if host == '127.0.0.1' else host}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
