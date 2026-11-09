"""Find Markdown source folders of a data tree ``<root>/<domain>/<subdir>``."""

from __future__ import annotations

from pathlib import Path

from wissenswiki_core.documents import list_documents


def markdown_domains(root: Path, relations_root: Path, *, subdir: str = "md", prefix: str = "",
                     exclude: list[Path] | None = None, create: bool = True) -> list[tuple[str, Path, Path]]:
    """(name, source, relation folder) per domain; symlinked subfolders become own domains.

    Sources equal to, inside or around an ``exclude`` path or an earlier source are skipped,
    as are sources without Markdown. With ``create`` the relation folders are made.
    """
    taken = [path.resolve() for path in exclude or []]
    candidates: list[tuple[str, Path]] = []
    for domain_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        md_dir = domain_dir / subdir
        if not md_dir.is_dir():
            continue
        candidates.append((f"{prefix}{domain_dir.name}", md_dir.resolve()))
        for link in sorted(md_dir.rglob("*")):
            if link.is_symlink() and link.is_dir():
                candidates.append((f"{prefix}{domain_dir.name}/{link.relative_to(md_dir).as_posix()}",
                                   link.resolve()))
    result = []
    for name, source in candidates:
        if any(source == other or source.is_relative_to(other) or other.is_relative_to(source) for other in taken):
            continue
        if not list_documents(source):
            continue
        relations = relations_root / name.removeprefix(prefix).replace("/", "--")
        if create:
            relations.mkdir(parents=True, exist_ok=True)
        taken.append(source)
        result.append((name, source, relations))
    return result
