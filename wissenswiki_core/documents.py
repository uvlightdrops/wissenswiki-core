"""Read Markdown documents with YAML front matter and H2 sections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


@dataclass(frozen=True)
class Block:
    title: str
    block_id: str | None
    content: str
    metadata: dict


@dataclass(frozen=True)
class Document:
    path: Path
    metadata: dict
    intro: str
    blocks: tuple[Block, ...]


class DocumentError(ValueError):
    """A document or its metadata cannot be read."""


def parse_document(path: Path, *, require_header: bool = True) -> Document:
    """Read YAML metadata and H2 sections without treating code as headings.

    Without ``require_header`` a file lacking front matter is read with empty metadata.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DocumentError(f"{path}: Datei nicht lesbar: {exc}") from exc
    if not require_header and not text.startswith("---\n"):
        intro, blocks = split_blocks(text)
        return Document(path, {}, intro, tuple(blocks))
    if not text.startswith("---\n"):
        raise DocumentError(f"{path}: YAML-Header fehlt")
    if "\n---\n" not in text:
        raise DocumentError(f"{path}: YAML-Header ist nicht abgeschlossen")
    front, body = text[4:].split("\n---\n", 1)
    try:
        metadata = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        raise DocumentError(f"{path}: YAML-Header ungültig: {exc}") from exc
    if not isinstance(metadata, dict):
        raise DocumentError(f"{path}: YAML-Header muss ein Objekt sein")
    relations = metadata.get("relations", [])
    if not isinstance(relations, list):
        raise DocumentError(f"{path}: relations muss eine Liste sein")
    for relation in relations:
        if not isinstance(relation, dict) or not all(
            isinstance(relation.get(key), str) and relation[key] for key in ("target", "type")
        ):
            raise DocumentError(f"{path}: Relation benötigt target und type als Text")
        if "source" in relation and not isinstance(relation["source"], str):
            raise DocumentError(f"{path}: source einer Relation muss Text sein")
    try:
        intro, blocks = split_blocks(body)
    except DocumentError as exc:
        raise DocumentError(f"{path}: {exc}") from exc
    return Document(path, metadata, intro, tuple(blocks))


def split_blocks(body: str) -> tuple[str, list[Block]]:
    """Split H2 sections while preserving fenced code and untagged sections."""
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    fence: str | None = None
    for line in body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        if fence is None and line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)
    blocks = []
    for heading, lines in sections[1:]:
        match = re.search(r"\s+\[([a-z0-9-]+)\]$", heading or "")
        title = (heading[:match.start()] if match else heading) or ""
        content, metadata = _extract_block_metadata(lines)
        blocks.append(Block(title, match.group(1) if match else None, content, metadata))
    return "\n".join(sections[0][1]), blocks


def _extract_block_metadata(lines: list[str]) -> tuple[str, dict]:
    content = []
    metadata = {}
    seen = False
    fence_char = None
    fence_length = 0
    block_meta = False
    yaml_lines = []

    for line in lines:
        if fence_char:
            closing = re.match(r"^ {0,3}(`+|~+)[ \t]*$", line)
            if (closing and closing.group(1)[0] == fence_char
                    and len(closing.group(1)) >= fence_length):
                if block_meta:
                    if seen:
                        raise DocumentError("Abschnitt enthält mehr als einen YAML-Block block-meta")
                    try:
                        parsed = yaml.safe_load("\n".join(yaml_lines))
                    except yaml.YAMLError as exc:
                        raise DocumentError(f"YAML-Block block-meta ungültig: {exc}") from exc
                    if not isinstance(parsed, dict):
                        raise DocumentError("YAML-Block block-meta muss ein Objekt sein")
                    metadata = parsed
                    seen = True
                else:
                    content.append(line)
                fence_char = None
                block_meta = False
                yaml_lines = []
            elif block_meta:
                yaml_lines.append(line)
            else:
                content.append(line)
            continue

        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if opening:
            marker, info = opening.groups()
            fence_char, fence_length = marker[0], len(marker)
            block_meta = re.fullmatch(r"(?i:yaml)\s+block-meta", info.strip()) is not None
            if block_meta:
                if content and content[-1] == "":
                    content.pop()
            else:
                content.append(line)
            continue

        content.append(line)

    if block_meta:
        raise DocumentError("YAML-Block block-meta ist nicht abgeschlossen")
    if seen:
        return "\n".join(content).strip("\n"), metadata
    return "\n".join(lines), {}



def list_documents(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file() and path.resolve().is_relative_to(root))
