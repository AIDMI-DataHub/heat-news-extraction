"""NewsSource Protocol -- common interface for all news source adapters.

Defines the structural typing contract that GoogleNewsSource, NewsDataSource,
and GNewsSource all satisfy. Uses typing.Protocol for duck-typing rather
than abc.ABC to avoid requiring inheritance.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.models.article import ArticleRef


@runtime_checkable
class NewsSource(Protocol):
    """Common interface for all news source adapters.

    Any class that implements an ``async def search(...)`` method with the
    matching signature satisfies this protocol via structural subtyping --
    no inheritance or registration needed.

    The ``state`` and ``search_term`` keyword-only parameters carry caller
    context required to construct :class:`ArticleRef` objects.  Every source
    adapter needs them because the search API responses do not include this
    information.
    """

    async def search(
        self,
        query: str,
        language: str,
        country: str = "IN",
        *,
        state: str = "",
        search_term: str = "",
    ) -> list[ArticleRef]:
        """Search for news articles matching *query*.

        Parameters
        ----------
        query:
            Search terms (may contain non-Latin scripts such as Devanagari
            or Tamil).
        language:
            ISO 639-1 language code (e.g. ``"hi"``, ``"ta"``).
        country:
            ISO 3166-1 alpha-2 country code.  Defaults to ``"IN"`` (India).
        state:
            Indian state or region name to attach to each result.
            Keyword-only.
        search_term:
            The original heat term used for the query, attached to each
            result for traceability.  Keyword-only.

        Returns
        -------
        list[ArticleRef]
            Parsed search results.  Returns an empty list on failure --
            implementations must never raise.
        """
        ...
