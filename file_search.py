"""Bounded local file indexing and ranking for launcher queries."""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fuzzy_search import normalize_text


MAX_INDEX_ENTRIES = 30_000
MAX_DIRECTORY_DEPTH = 8
MAX_SEARCH_RESULTS = 15


@dataclass(frozen=True)
class FileSearchResult:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def description(self) -> str:
        return str(self.path.parent)


def index_home_files(
    root: Path | None = None,
    *,
    max_entries: int = MAX_INDEX_ENTRIES,
    max_depth: int = MAX_DIRECTORY_DEPTH,
) -> tuple[Path, ...]:
    """Index visible files/directories under home without following symlinks."""
    home = (root or Path.home()).expanduser().resolve()
    if not home.is_dir():
        raise OSError(f"Kullanıcı dizini bulunamadı: {home}")

    indexed: list[Path] = []
    pending = [(home, 0)]
    visited = 0
    while pending and visited < max_entries:
        directory, depth = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in sorted(entries, key=lambda item: item.name.casefold()):
                    visited += 1
                    if visited > max_entries:
                        break
                    if entry.name.startswith("."):
                        continue
                    try:
                        if entry.is_symlink():
                            continue
                        is_directory = entry.is_dir(follow_symlinks=False)
                        is_file = entry.is_file(follow_symlinks=False)
                    except OSError:
                        continue
                    if not is_directory and not is_file:
                        continue

                    path = Path(entry.path)
                    indexed.append(path)
                    if depth < max_depth and is_directory:
                        pending.append((path, depth + 1))
        except OSError:
            if directory == home:
                raise

    return tuple(indexed)


def resolve_home_path(path: Path, *, root: Path | None = None) -> Path:
    """Resolve an indexed item at activation time and reject paths outside home."""
    home = (root or Path.home()).expanduser().resolve()
    if path.is_symlink():
        raise ValueError("Sembolik bağlantılar dosya aramasında açılamaz.")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(home):
        raise ValueError("Yalnızca kullanıcı dizini altındaki dosyalar açılabilir.")
    if not resolved.is_file() and not resolved.is_dir():
        raise ValueError("Seçilen dosya veya klasör artık kullanılamıyor.")
    return resolved


def search_files(
    query: str,
    indexed_paths: Sequence[Path],
    *,
    limit: int = 12,
) -> list[FileSearchResult]:
    normalized_query = normalize_text(" ".join(query.split()))
    if not normalized_query or limit <= 0:
        return []

    result_limit = min(limit, MAX_SEARCH_RESULTS)
    ranked: list[tuple[int, str, Path]] = []
    for path in indexed_paths:
        name = normalize_text(path.name)
        full_path = normalize_text(str(path))
        if name == normalized_query:
            score = 1200
        elif name.startswith(normalized_query):
            score = 1000 - min(100, len(name) - len(normalized_query))
        elif any(
            word.startswith(normalized_query) for word in name.split()
        ):
            score = 900
        elif normalized_query in name:
            score = 800 - name.find(normalized_query)
        elif normalized_query in full_path:
            score = 500 - full_path.find(normalized_query)
        else:
            continue
        ranked.append((score, full_path, path))

    ranked.sort(key=lambda result: (-result[0], result[1]))
    return [FileSearchResult(path) for _, _, path in ranked[:result_limit]]
