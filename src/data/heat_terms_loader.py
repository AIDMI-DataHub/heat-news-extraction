"""Load, validate, and query heat-related terminology for the news extraction pipeline.

Provides Pydantic-validated models for heat terms across multiple Indian languages,
organized by category and register. Data is loaded from heat_terms.json and cached
via lru_cache so the file is read only once per process.
"""

from __future__ import annotations

import json
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pydantic v2 warns when a field name shadows a BaseModel method.
# "register" is the correct domain term and works fine despite the warning.
warnings.filterwarnings(
    "ignore",
    message='Field name "register" in "HeatTerm" shadows an attribute in parent "BaseModel"',
    category=UserWarning,
)

_DATA_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
TermCategory = Literal[
    "heatwave",
    "death_stroke",
    "water_crisis",
    "power_cuts",
    "crop_damage",
    "human_impact",
    "government_response",
    "temperature",
]

TermRegister = Literal["formal", "colloquial", "journalistic", "borrowed"]

TERM_CATEGORIES: frozenset[str] = frozenset(
    {
        "heatwave",
        "death_stroke",
        "water_crisis",
        "power_cuts",
        "crop_damage",
        "human_impact",
        "government_response",
        "temperature",
    }
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class HeatTerm(BaseModel):
    """A single heat-related term with its register classification."""

    model_config = ConfigDict(frozen=True)

    term: str = Field(..., min_length=1)
    register: Literal["formal", "colloquial", "journalistic", "borrowed"]


class CategoryTerms(BaseModel):
    """Collection of terms within a single category."""

    model_config = ConfigDict(frozen=True)

    terms: list[HeatTerm] = Field(min_length=1)


class LanguageTerms(BaseModel):
    """All categories and their terms for a single language."""

    model_config = ConfigDict(frozen=True)

    name: str
    categories: dict[TermCategory, CategoryTerms]

    @field_validator("categories")
    @classmethod
    def validate_all_categories_present(
        cls, v: dict[TermCategory, CategoryTerms]
    ) -> dict[TermCategory, CategoryTerms]:
        """Ensure all 8 term categories are present."""
        present = set(v.keys())
        missing = TERM_CATEGORIES - present
        if missing:
            raise ValueError(
                f"Missing required categories: {sorted(missing)}. "
                f"All 8 categories must be present: {sorted(TERM_CATEGORIES)}"
            )
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
    for category in language.categories.values():
        for heat_term in category.terms:
            terms.append(heat_term.term)
    return terms


def get_terms_by_category(lang: str, category: TermCategory) -> list[str]:
    """Return terms for a specific language and category combination.

    Args:
        lang: ISO 639-1 language code (e.g. 'en', 'hi').
        category: One of the 8 term categories.

    Returns:
        List of term strings, or empty list if language or category not found.
    """
    data = load_heat_terms()
    if lang not in data.languages:
        return []
    language = data.languages[lang]
    if category not in language.categories:
        return []
    return [t.term for t in language.categories[category].terms]


def get_borrowed_terms(lang: str) -> list[str]:
    """Return only terms with register 'borrowed' for a language.

    Args:
        lang: ISO 639-1 language code (e.g. 'en', 'hi').

    Returns:
        List of borrowed term strings, or empty list if language not found.
    """
    data = load_heat_terms()
    if lang not in data.languages:
        return []
    language = data.languages[lang]
    terms: list[str] = []
    for category in language.categories.values():
        for heat_term in category.terms:
            if heat_term.register == "borrowed":
                terms.append(heat_term.term)
    return terms


def get_all_term_languages() -> list[str]:
    """Return all language codes present in the heat terms dictionary.

    Returns:
        List of language code strings (e.g. ['en', 'hi']).
    """
    return list(load_heat_terms().languages.keys())


def get_terms_by_register(lang: str, register: TermRegister) -> list[str]:
    """Return all terms with a specific register for a language.

    Args:
        lang: ISO 639-1 language code (e.g. 'en', 'hi').
        register: One of 'formal', 'colloquial', 'journalistic', 'borrowed'.

    Returns:
        List of term strings matching the register, or empty list if language not found.
    """
    data = load_heat_terms()
    if lang not in data.languages:
        return []
    language = data.languages[lang]
    terms: list[str] = []
    for category in language.categories.values():
        for heat_term in category.terms:
            if heat_term.register == register:
                terms.append(heat_term.term)
    return terms
