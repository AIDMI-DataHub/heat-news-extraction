"""News source adapters for the heat news extraction pipeline.

This sub-package holds adapters for fetching news from various sources
including Google News RSS, NewsData.io, and GNews APIs.
"""

from ._protocol import NewsSource
from .google_news import GoogleNewsSource

__all__ = ["NewsSource", "GoogleNewsSource"]
