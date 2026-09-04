from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..settings import settings


@dataclass
class Source:
    title: str
    path: str
    language: str
    level: str
    content: str
    score: int = 0


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def load_sources() -> list[Source]:
    sources = []
    for path in settings.obsidian_path.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        meta, body = _frontmatter(text)
        if meta.get("status", "approved") != "approved":
            continue
        sources.append(Source(
            title=meta.get("title", path.stem), path=str(path.relative_to(settings.obsidian_path)),
            language=meta.get("language", "Shared"), level=meta.get("level", "A0"), content=body,
        ))
    return sources


def search(query: str, language: str, level: str, limit: int = 3) -> list[Source]:
    terms = set(re.findall(r"[a-zа-яáéíóúüñ]+", query.lower()))
    ranked = []
    for source in load_sources():
        if source.language not in (language, "Shared"):
            continue
        if source.level not in (level, "A0", "Shared"):
            continue
        haystack = f"{source.title} {source.content}".lower()
        source.score = sum(3 if term in source.title.lower() else 1 for term in terms if term in haystack)
        ranked.append(source)
    ranked.sort(key=lambda item: item.score, reverse=True)
    return [item for item in ranked if item.score > 0][:limit] or ranked[:1]

