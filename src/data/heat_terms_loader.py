"""Load, validate, and query heat-related terminology for the news extraction pipeline.

Provides Pydantic-validated models for heat terms across multiple Indian languages,
organized by category. Data is loaded from heat_terms.json and cached via lru_cache
so the file is read only once per process.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

_DATA_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
TermCategory = Literal[
    "weather",
    "health",
    "water",
    "power",
    "agriculture",
    "labor",
    "governance",
    "urban_infra",
    "education",
    "temperature",
]

TERM_CATEGORIES: frozenset[str] = frozenset(
    {
        "weather",
        "health",
        "water",
        "power",
        "agriculture",
        "labor",
        "governance",
        "urban_infra",
        "education",
        "temperature",
    }
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class LanguageTerms(BaseModel):
    """All categories and their terms for a single language."""

    model_config = ConfigDict(frozen=True)

    name: str
    categories: dict[TermCategory, list[str]]

    @field_validator("categories")
    @classmethod
    def validate_all_categories_present(
        cls, v: dict[TermCategory, list[str]]
    ) -> dict[TermCategory, list[str]]:
        """Ensure all 10 term categories are present."""
        present = set(v.keys())
        missing = TERM_CATEGORIES - present
        if missing:
            raise ValueError(
                f"Missing required categories: {sorted(missing)}. "
                f"All 10 categories must be present: {sorted(TERM_CATEGORIES)}"
            )
        # Ensure each category has at least one term
        for cat, terms in v.items():
            if not terms:
                raise ValueError(f"Category '{cat}' must have at least one term")
        return v


class HeatTermsDictionary(BaseModel):
    """Top-level container for the heat terms dictionary."""

    model_config = ConfigDict(frozen=True)

    version: str
    languages: dict[str, LanguageTerms]


# ---------------------------------------------------------------------------
# Loader (cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_heat_terms() -> HeatTermsDictionary:
    """Load and validate all heat terms from the master JSON file.

    Cached: only reads disk and validates once per process.

    Returns:
        HeatTermsDictionary: Validated heat terms containing all languages.

    Raises:
        FileNotFoundError: If heat_terms.json is missing.
        pydantic.ValidationError: If data is malformed or contains invalid values.
    """
    data_path = _DATA_DIR / "heat_terms.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return HeatTermsDictionary.model_validate(raw)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------
def get_terms_for_language(lang: str) -> list[str]:
    """Return all terms flattened across all categories for a language.

    Args:
        lang: ISO 639-1 language code (e.g. 'en', 'hi').

    Returns:
        List of term strings, or empty list if language not in dictionary.
    """
    data = load_heat_terms()
    if lang not in data.languages:
        return []
    language = data.languages[lang]
    terms: list[str] = []
    for category_terms in language.categories.values():
        terms.extend(category_terms)
    return terms


def get_terms_by_category(lang: str, category: TermCategory) -> list[str]:
    """Return terms for a specific language and category combination.

    Args:
        lang: ISO 639-1 language code (e.g. 'en', 'hi').
        category: One of the 10 term categories.

    Returns:
        List of term strings, or empty list if language or category not found.
    """
    data = load_heat_terms()
    if lang not in data.languages:
        return []
    language = data.languages[lang]
    if category not in language.categories:
        return []
    return list(language.categories[category])


def get_all_term_languages() -> list[str]:
    """Return all language codes present in the heat terms dictionary.

    Returns:
        List of language code strings (e.g. ['en', 'hi']).
    """
    return list(load_heat_terms().languages.keys())
