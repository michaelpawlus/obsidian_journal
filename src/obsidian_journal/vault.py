from __future__ import annotations

import shutil
from pathlib import Path

import frontmatter as fm

from obsidian_journal.config import Config
from obsidian_journal.models import Frontmatter, Note

SKIP_DIRS = {".obsidian", ".trash", "Templates"}
SKIP_PREFIXES = (".smtcmp_",)


def _should_skip(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        if part in SKIP_DIRS or any(part.startswith(p) for p in SKIP_PREFIXES):
            return True
    return False


def list_notes(config: Config) -> list[Note]:
    notes: list[Note] = []
    for md_file in sorted(config.vault_path.rglob("*.md")):
        rel = md_file.relative_to(config.vault_path)
        if _should_skip(rel):
            continue
        note = read_note(config, rel)
        if note:
            notes.append(note)
    return notes


def read_note(config: Config, rel_path: Path | str) -> Note | None:
    rel_path = Path(rel_path)
    full_path = config.vault_path / rel_path
    if not full_path.exists():
        return None
    try:
        post = fm.load(full_path)
    except Exception:
        return None
    meta = dict(post.metadata) if post.metadata else {}
    front = Frontmatter(
        date=str(meta.pop("date", "")),
        type=str(meta.pop("type", "")),
        tags=meta.pop("tags", []) or [],
        related=meta.pop("related", []) or [],
        extra=meta,
    )
    folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""
    title = rel_path.stem
    return Note(title=title, body=post.content, frontmatter=front, folder=folder)


def write_note(config: Config, note: Note) -> Path:
    folder = config.vault_path / note.folder if note.folder else config.vault_path
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / note.filename
    post = fm.Post(note.body, **note.frontmatter.to_dict())
    dest.write_text(fm.dumps(post), encoding="utf-8")
    return dest


def move_note(config: Config, src_rel: Path | str, dest_rel: Path | str) -> Path:
    src = config.vault_path / Path(src_rel)
    dest = config.vault_path / Path(dest_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


def get_all_note_titles(config: Config) -> list[str]:
    titles: list[str] = []
    for md_file in sorted(config.vault_path.rglob("*.md")):
        rel = md_file.relative_to(config.vault_path)
        if _should_skip(rel):
            continue
        titles.append(md_file.stem)
    return titles
