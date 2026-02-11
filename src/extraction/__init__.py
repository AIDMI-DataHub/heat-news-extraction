"""Article text extraction for the heat news extraction pipeline.

Provides Google News URL resolution and trafilatura-based article text
extraction with async batch processing and bounded concurrency.

Public API
----------
- :func:`extract_articles` -- batch-extract a list of ArticleRef into Articles
- :func:`extract_article` -- extract a single ArticleRef into an Article
- :func:`resolve_url` -- resolve Google News redirect URLs to actual article URLs
"""

from src.extraction._extractor import extract_article, extract_articles
from src.extraction._resolver import resolve_url

__all__ = ["extract_articles", "extract_article", "resolve_url"]
