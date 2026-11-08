"""Unicode-aware dependency-free fuzzy ranking for desktop applications."""

import unicodedata
from collections.abc import Mapping, Sequence

from desktop_parser import DesktopApplication


def normalize_text(value: str) -> str:
    """Normalize Unicode and accents for matching without changing display text."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).replace("ı", "i")


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    if left == right:
        return True
    if len(left) > len(right):
        left, right = right, left
    i = j = differences = 0
    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            i += 1
            j += 1
            continue
        differences += 1
        if differences > 1:
            return False
        if len(left) == len(right):
            i += 1
        j += 1
    return differences + (j < len(right)) <= 1


def _score_text(query: str, candidate: str, *, name_field: bool) -> int:
    if not query or not candidate:
        return 0
    if candidate == query:
        return 1200 if name_field else 700
    if candidate.startswith(query):
        return (1000 if name_field else 610) - min(100, len(candidate) - len(query))

    words = candidate.split()
    word_positions = [word.find(query) for word in words]
    if any(position == 0 for position in word_positions):
        return (900 if name_field else 560) - min(
            100, next(index for index, position in enumerate(word_positions) if position == 0) * 8
        )
    if query in candidate:
        return (800 if name_field else 500) - min(100, candidate.find(query))

    query_words = query.split()
    if len(query_words) > 1:
        cursor = 0
        matched = True
        for query_word in query_words:
            position = candidate.find(query_word, cursor)
            if position < 0:
                matched = False
                break
            cursor = position + len(query_word)
        if matched:
            return (740 if name_field else 450) - min(100, cursor - len(query))

    for word in words:
        if len(query) >= 3 and _edit_distance_at_most_one(query, word):
            return (570 if name_field else 330) - abs(len(word) - len(query)) * 10

    cursor = 0
    positions: list[int] = []
    for character in query.replace(" ", ""):
        found = candidate.find(character, cursor)
        if found < 0:
            return 0
        positions.append(found)
        cursor = found + 1
    if len(positions) < 2:
        return 0
    span = positions[-1] - positions[0] + 1
    gaps = span - len(positions)
    minimum_score = 420 if name_field else 250
    return max(minimum_score, (680 if name_field else 390) - gaps * 12 - positions[0])


def search_applications(
    applications: Sequence[DesktopApplication],
    query: str,
    limit: int = 8,
    history_ids: Sequence[str] | None = None,
    history_scores: Mapping[str, int] | None = None,
    favorite_ids: Sequence[str] | None = None,
) -> list[DesktopApplication]:
    normalized_query = normalize_text(" ".join(query.split()))
    if not normalized_query or limit <= 0:
        return []

    recent_ids = set(history_ids or ())
    recent_scores = history_scores or {}
    favorites = set(favorite_ids or ())
    ranked: list[tuple[int, str, str, DesktopApplication]] = []
    seen: set[str] = set()
    for application in applications:
        desktop_id = getattr(application, "desktop_id", "") or application.name
        if desktop_id in seen:
            continue
        seen.add(desktop_id)

        name = normalize_text(application.name)
        score = _score_text(normalized_query, name, name_field=True)
        generic_name = normalize_text(getattr(application, "generic_name", ""))
        score = max(score, _score_text(normalized_query, generic_name, name_field=False))

        if not score:
            fields = [
                getattr(application, "executable", ""),
                desktop_id,
                *getattr(application, "keywords", ()),
                *getattr(application, "categories", ()),
            ]
            for field in fields:
                score = max(
                    score,
                    _score_text(
                        normalized_query, normalize_text(field), name_field=False
                    ),
                )
        if not score:
            score = _score_text(
                normalized_query,
                normalize_text(getattr(application, "comment", "")),
                name_field=False,
            )
        if not score:
            continue

        if desktop_id in favorites:
            score += 12
        score += min(80, max(0, recent_scores.get(desktop_id, 0)))
        if desktop_id in recent_ids and desktop_id not in recent_scores:
            score += 40
        ranked.append((score, name, desktop_id, application))

    ranked.sort(key=lambda result: (-result[0], result[1], result[2]))
    return [result[3] for result in ranked[:limit]]
