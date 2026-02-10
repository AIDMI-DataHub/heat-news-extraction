"""Pydantic data models for the heat news extraction pipeline.

This sub-package holds structured data models including Article,
SearchResult, and other domain objects used throughout the pipeline.
"""

from .article import Article, ArticleRef, IST

__all__ = ["Article", "ArticleRef", "IST"]
