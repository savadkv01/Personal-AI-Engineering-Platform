"""Document loaders. Return plain text + a title + light metadata hints.

Markdown/text parse optional YAML front-matter (``--- ... ---``) to seed
``title``/``tags``/``scope``. PDF/EPUB imports are lazy so Markdown/code
ingestion never depends on those libraries being installed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LoadedDoc:
    text: str
    title: str
    tags: list[str] = field(default_factory=list)
    scope: str | None = None
    extra: dict = field(default_factory=dict)


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Split leading ``--- ... ---`` YAML front-matter from the body."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 4:].lstrip("\n")
            try:
                meta = yaml.safe_load(block) or {}
                if isinstance(meta, dict):
                    return meta, body
            except yaml.YAMLError:
                pass
    return {}, text


def _title_from_markdown(body: str, fallback: str) -> str:
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def _load_text(path: Path) -> LoadedDoc:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_front_matter(raw)
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    title = str(meta.get("title") or _title_from_markdown(body, path.stem))
    return LoadedDoc(text=body, title=title, tags=[str(t) for t in tags],
                     scope=meta.get("scope"), extra={"front_matter": bool(meta)})


def _load_code(path: Path) -> LoadedDoc:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return LoadedDoc(text=raw, title=path.name, extra={"lang": path.suffix.lstrip(".")})


def _load_pdf(path: Path) -> LoadedDoc:
    from pypdf import PdfReader  # lazy

    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages]
    return LoadedDoc(text="\n\n".join(pages), title=path.stem,
                     extra={"pages": len(pages)})


def _load_epub(path: Path) -> LoadedDoc:
    import ebooklib  # lazy
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        parts.append(soup.get_text(" ", strip=True))
    title = path.stem
    meta_title = book.get_metadata("DC", "title")
    if meta_title:
        title = meta_title[0][0]
    return LoadedDoc(text="\n\n".join(parts), title=str(title))


_LOADERS = {
    ".md": _load_text, ".markdown": _load_text, ".txt": _load_text, ".rst": _load_text,
    ".pdf": _load_pdf,
    ".epub": _load_epub,
}


def load_document(path: str) -> LoadedDoc:
    p = Path(path)
    loader = _LOADERS.get(p.suffix.lower(), _load_code)
    return loader(p)


def iter_files(paths: list[str], exclude_dirs: set[str], exclude_names: set[str]):
    """Yield file paths under the given files/dirs, honoring excludes."""
    for base in paths:
        bp = Path(base)
        if bp.is_file():
            if bp.name not in exclude_names:
                yield str(bp)
            continue
        for root, dirs, files in os.walk(bp):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
            for name in sorted(files):
                if name in exclude_names or name.startswith("."):
                    continue
                yield str(Path(root) / name)
