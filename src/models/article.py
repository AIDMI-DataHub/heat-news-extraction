"""Pydantic v2 data models for heat-related news articles.

Defines ArticleRef (lightweight search result) and Article (complete article
with extraction results). All dates are normalized to IST (Asia/Kolkata).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
)

IST = ZoneInfo("Asia/Kolkata")


def coerce_naive_to_ist(value: Any) -> Any:
    """If a naive datetime is provided, assume it is IST.

    Some news sources return dates without timezone info.
    Rather than rejecting them, we assume IST since all sources
    are India-focused.
    """
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value


ISTAwareDatetime = Annotated[AwareDatetime, BeforeValidator(coerce_naive_to_ist)]


class ArticleRef(BaseModel):
    """Lightweight reference from search results (no full text yet).

    Created by source adapters (Google News RSS, NewsData.io, GNews)
    during the search phase. Contains only metadata available from
    search results.
    """

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    date: ISTAwareDatetime
    language: str = Field(
        ..., pattern=r"^(en|hi|ta|te|bn|mr|gu|kn|ml|or|pa|as|ur|ne)$"
    )
    state: str = Field(..., min_length=1)
    district: str | None = None
    search_term: str = Field(..., min_length=1)

    @field_validator("date")
    @classmethod
    def normalize_to_ist(cls, v: datetime) -> datetime:
        """Normalize any timezone-aware datetime to IST (Asia/Kolkata)."""
        return v.astimezone(IST)


class Article(ArticleRef):
    """Complete article with extracted full text and relevance scoring.

    Created by enriching an ArticleRef with full text extraction
    (Phase 7) and relevance scoring (Phase 8). Inherits all fields
    from ArticleRef plus full_text and relevance_score.
    """

    full_text: str | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
