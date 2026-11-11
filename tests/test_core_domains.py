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


def test_block_meta_is_extracted_from_content_and_exposed_as_attributes(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    storage = tmp_path / "relations"
    storage.mkdir()
    (source / "buch.md").write_text(
        "---\nproject: Books\n---\n# Buch\n## Abschnitt [abschnitt]\n\n"
        "```yaml block-meta\nupdated: '2026-11-11 05'\nstatus: active\nrelations: []\n```\n\n"
        "Sichtbarer Inhalt.\n"
    )

    node = next(item for item in DocumentDomain(source, storage).snapshot()["blocks"]
                if item["id"] == "doc:buch.md#abschnitt")

    assert node["text"] == "Sichtbarer Inhalt."
    assert node["attributes"]["block_metadaten"] == {
        "updated": "2026-11-11 05", "status": "active", "relations": []
    }


def test_regular_yaml_fence_stays_in_block_content(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    storage = tmp_path / "relations"
    storage.mkdir()
    content = "```yaml\nstatus: draft\n```"
    (source / "buch.md").write_text(f"# Buch\n## Abschnitt [abschnitt]\n{content}")

    node = next(item for item in DocumentDomain(source, storage, lenient=True).snapshot()["blocks"]
                if item["id"] == "doc:buch.md#abschnitt")

    assert node["text"] == content
    assert node["attributes"]["block_metadaten"] == {}


def test_invalid_block_meta_is_reported_as_document_error(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    storage = tmp_path / "relations"
    storage.mkdir()
    (source / "buch.md").write_text(
        "# Buch\n## Abschnitt [abschnitt]\n```yaml block-meta\nstatus: [\n```\n"
    )

    snapshot = DocumentDomain(source, storage, lenient=True).snapshot()

    assert snapshot["blocks"] == []
    assert any("YAML-Block block-meta ungültig" in error for error in snapshot["errors"])


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


@pytest.mark.parametrize("text,message", [
    ("# Ohne Header\n", "YAML-Header fehlt"),
    ("---\ntitle: Offen\n", "YAML-Header ist nicht abgeschlossen"),
])
def test_header_errors_distinguish_missing_from_unclosed(tmp_path, text, message):
    source = tmp_path / "docs"
    source.mkdir()
    (source / "note.md").write_text(text)
    (tmp_path / "relations").mkdir()
    snapshot = DocumentDomain(source, tmp_path / "relations").snapshot()
    assert snapshot["blocks"] == []
    assert len(snapshot["errors"]) == 1
    assert snapshot["errors"][0].endswith(": " + message)
