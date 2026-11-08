"""Small dependency-free fuzzy matching for launcher queries."""

from collections.abc import Sequence

from desktop_parser import DesktopApplication


def _match_score(query: str, candidate: str) -> int:
    if not query or not candidate:
        return 0
    if candidate == query:
        return 1000
    if candidate.startswith(query):
        return 800 - (len(candidate) - len(query))

    position = candidate.find(query)
    if position >= 0:
        return 600 - position

    positions: list[int] = []
    cursor = 0
    for character in query:
        found = candidate.find(character, cursor)
        if found < 0:
            return 0
        positions.append(found)
        cursor = found + 1

    span = positions[-1] - positions[0] + 1
    gaps = span - len(query)
    return max(1, 300 + len(query) * 4 - gaps * 8 - positions[0])


def search_applications(
    applications: Sequence[DesktopApplication],
    query: str,
    limit: int = 8,
) -> list[DesktopApplication]:
    normalized_query = " ".join(query.casefold().split())
    if not normalized_query or limit <= 0:
        return []

    ranked: list[tuple[int, str, DesktopApplication]] = []
    for application in applications:
        name = application.name.casefold()
        description = application.comment.casefold()
        name_score = _match_score(normalized_query, name)
        description_score = _match_score(normalized_query, description) // 3
        score = max(name_score, description_score)
        if score:
            ranked.append((score, name, application))

    ranked.sort(key=lambda result: (-result[0], result[1]))
    return [result[2] for result in ranked[:limit]]
