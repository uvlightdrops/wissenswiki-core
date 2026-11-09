import pytest

from wissenswiki_core.workspace import Workspace, WorkspaceConflict, WorkspaceError


def test_blocks_relations_and_order_persist_as_markdown(tmp_path):
    workspace = Workspace(tmp_path)
    essay = workspace.create("Essay", "Einleitung")
    first = workspace.create("Erster Gedanke", "Erster Text")
    second = workspace.create("", "Zweiter Text")
    assert first["attributes"]["metadaten"]["formulation_origin"] == "human"
    essay = workspace.update(essay["id"], essay["revision"], "relate",
                             {"target": first["id"], "type": "part-of"})
    essay = workspace.update(essay["id"], essay["revision"], "parts",
                             {"parts": [first["id"], second["id"]]})
    essay = workspace.update(essay["id"], essay["revision"], "parts",
                             {"parts": [second["id"], first["id"]]})

    reopened = {block["id"]: block for block in Workspace(tmp_path).list_blocks()}
    assert reopened[essay["id"]]["relations"] == [{"target": first["id"], "type": "part-of"}]
    assert reopened[essay["id"]]["parts"] == [second["id"], first["id"]]
    assert (tmp_path / f'{first["id"]}.md').read_text(encoding="utf-8").endswith("Erster Text")
    assert "formulation_origin: human" in (tmp_path / f'{first["id"]}.md').read_text(encoding="utf-8")


def test_external_edits_cause_conflict_without_overwriting(tmp_path):
    workspace = Workspace(tmp_path)
    block = workspace.create("Titel", "Alter Text")
    path = tmp_path / f'{block["id"]}.md'
    path.write_text(path.read_text(encoding="utf-8").replace("Alter Text", "Externer Text"), encoding="utf-8")
    with pytest.raises(WorkspaceConflict, match="zwischenzeitlich geändert"):
        workspace.update(block["id"], block["revision"], "save", {"title": "Titel", "text": "Neu"})
    assert "Externer Text" in path.read_text(encoding="utf-8")


def test_invalid_targets_duplicate_relations_and_symlinks_are_rejected(tmp_path):
    workspace = Workspace(tmp_path)
    first = workspace.create("Eins", "")
    second = workspace.create("Zwei", "")
    with pytest.raises(WorkspaceError):
        workspace.update(first["id"], first["revision"], "relate", {"target": "../x", "type": "ref"})
    with pytest.raises(WorkspaceError):
        workspace.update(first["id"], first["revision"], "parts", {"parts": [first["id"]]})
    first = workspace.update(first["id"], first["revision"], "relate", {"target": second["id"], "type": "ref"})
    with pytest.raises(WorkspaceError, match="bereits"):
        workspace.update(first["id"], first["revision"], "relate", {"target": second["id"], "type": "ref"})
    first = workspace.update(first["id"], first["revision"], "unrelate", {"index": 0})
    assert first["relations"] == []
    link = tmp_path / ("a" * 32 + ".md")
    link.symlink_to(tmp_path / f'{second["id"]}.md')
    with pytest.raises(WorkspaceError, match="Links"):
        workspace.list_blocks()
