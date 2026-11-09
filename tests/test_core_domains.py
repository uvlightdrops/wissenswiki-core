import json
from pathlib import Path

import pytest

from wissenswiki_core.discovery import markdown_domains
from wissenswiki_core.domains import DocumentDomain
from wissenswiki_core.workspace import WorkspaceConflict, WorkspaceError


def test_document_nodes_and_relations_are_read_without_modifying_sources(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    storage = tmp_path / "relations"
    storage.mkdir()
    original = "---\nstatus: draft\ncreated: 2026-11-08\nrelations:\n  - source: '#one'\n    target: 'other.md#two'\n    type: extends\n---\n# First\n## One [one]\nText\n## Unstable\nMore\n"
    first = source / "first.md"
    first.write_text(original)
    (source / "other.md").write_text("---\n{}\n---\n# Second\n## Two [two]\nOther\n")
    domain = DocumentDomain(source, storage)
    snapshot = domain.snapshot()
    nodes = {node["id"]: node for node in snapshot["blocks"]}
    assert nodes["doc:first.md#one"]["relations"] == [{"target": "doc:other.md#two", "type": "extends"}]
    assert nodes["doc:first.md#one"]["attributes"]["block_id"] == "one"
    assert nodes["doc:first.md#one"]["attributes"]["dokument_metadaten"]["status"] == "draft"
    assert nodes["doc:first.md"]["attributes"]["dokument_metadaten"]["created"] == "2026-11-08"
    assert nodes["doc:first.md"]["attributes"]["ordner"] == "."
    assert nodes["doc:first.md#!unstable-1"]["linkable"] is False
    data = {"id": "doc:first.md#one", "target": "doc:other.md#two",
            "type": "references", "revision": snapshot["revision"]}
    updated = domain.relate(data)
    assert domain.snapshot() == updated
    assert first.read_text() == original
    assert json.loads((storage / "dokument-beziehungen.json").read_text()) == [{
        "source": "doc:first.md#one", "target": "doc:other.md#two", "type": "references"
    }]
    with pytest.raises(WorkspaceConflict):
        domain.relate(data)
    data.update(revision=updated["revision"], target="doc:first.md#!unstable-1")
    with pytest.raises(WorkspaceError, match="stabiler ID"):
        domain.relate(data)




def test_lenient_domain_reads_headerless_files_and_derives_section_ids(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    storage = tmp_path / "relations"
    storage.mkdir()
    text = "# Buch\n## Grüße aus Köln\nA\n## Grüße aus Köln\nB\n## Fest [fest]\nC\n"
    (source / "buch.md").write_text(text)

    assert DocumentDomain(source, storage).snapshot()["blocks"] == []
    snapshot = DocumentDomain(source, storage, lenient=True).snapshot()
    ids = [node["id"] for node in snapshot["blocks"]]
    assert ids == ["doc:buch.md", "doc:buch.md#auto-gruesse-aus-koeln",
                   "doc:buch.md#auto-gruesse-aus-koeln-2", "doc:buch.md#fest"]
    assert all(node["linkable"] for node in snapshot["blocks"])
    assert (source / "buch.md").read_text() == text


def _write(path: Path, text: str = "# Titel\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_markdown_domains_include_symlinked_folders_and_skip_served_sources(tmp_path):
    root = tmp_path / "data"
    _write(root / "anthro" / "md" / "buch" / "a.md")
    (root / "leer" / "md").mkdir(parents=True)
    _write(tmp_path / "extern" / "b.md")
    (root / "anthro" / "md" / "extern").symlink_to(tmp_path / "extern", target_is_directory=True)
    _write(tmp_path / "doc" / "c.md")
    (root / "anthro" / "md" / "doc").symlink_to(tmp_path / "doc", target_is_directory=True)
    relations = tmp_path / "rel"

    assert markdown_domains(root, relations, prefix="ki:", create=False) and not relations.exists()
    found = markdown_domains(root, relations, prefix="ki:", exclude=[tmp_path / "doc"])

    assert [(name, source) for name, source, _ in found] == [
        ("ki:anthro", (root / "anthro" / "md").resolve()),
        ("ki:anthro/extern", (tmp_path / "extern").resolve()),
    ]
    assert [path for _, _, path in found] == [relations / "anthro", relations / "anthro--extern"]
    assert all(path.is_dir() for _, _, path in found)
