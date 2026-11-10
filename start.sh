#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${ROOT_DIR}/wiki.yaml"
cd -- "${ROOT_DIR}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    printf 'Konfiguration fehlt: %s\n' "${CONFIG_FILE}" >&2
    printf 'Mit "cp wiki.example.yaml wiki.yaml" anlegen und dann bearbeiten.\n' >&2
    exit 1
fi

if [[ -x "${ROOT_DIR}/.venv/bin/wissenswiki" ]]; then
    WISSENSWIKI="${ROOT_DIR}/.venv/bin/wissenswiki"
elif command -v wissenswiki >/dev/null 2>&1; then
    WISSENSWIKI="$(command -v wissenswiki)"
else
    printf 'Befehl "wissenswiki" nicht gefunden. Installiere das Projekt mit:\n' >&2
    printf '  python3 -m pip install -e .\n' >&2
    exit 127
fi

exec "${WISSENSWIKI}" serve --config "${CONFIG_FILE}" "$@"
