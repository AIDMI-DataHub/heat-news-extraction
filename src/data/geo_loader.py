"""Load, validate, and query geographic data for the heat news extraction pipeline.

Provides Pydantic-validated models for Indian states/UTs, districts, and
language mappings. Data is loaded from india_geo.json and cached via lru_cache
so the file is read only once per process.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_DATA_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Supported language codes (ISO 639-1 / 639-2 where no -1 exists)
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {"en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur", "ne"}
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class District(BaseModel):
    """A single district within a state or union territory."""

    model_config = ConfigDict(frozen=True)

    name: str
    slug: str


class StateUT(BaseModel):
    """An Indian state or union territory with its districts and language mappings."""

    model_config = ConfigDict(frozen=True)

    name: str
    slug: str
    type: Literal["state", "ut"]
    languages: list[str] = Field(min_length=1)
    districts: list[District] = Field(min_length=1)

    @field_validator("languages")
    @classmethod
    def validate_language_codes(cls, v: list[str]) -> list[str]:
        """Ensure all language codes are within the 14 supported codes."""
        unsupported = set(v) - SUPPORTED_LANGUAGES
        if unsupported:
            raise ValueError(
                f"Unsupported language code(s): {sorted(unsupported)}. "
                f"Must be one of: {sorted(SUPPORTED_LANGUAGES)}"
            )
        return v


class GeoData(BaseModel):
    """Top-level container for all geographic data."""

    model_config = ConfigDict(frozen=True)

    states: list[StateUT]


# ---------------------------------------------------------------------------
# Loader (cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_geo_data() -> GeoData:
    """Load and validate all geographic data from the master JSON file.

    Cached: only reads disk and validates once per process.

    Returns:
        GeoData: Validated geographic data containing all states/UTs.

    Raises:
        FileNotFoundError: If india_geo.json is missing.
        pydantic.ValidationError: If data is malformed or contains invalid values.
    """
    data_path = _DATA_DIR / "india_geo.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return GeoData.model_validate(raw)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------
def get_all_regions() -> list[StateUT]:
    """Return all 36 states and union territories."""
    return load_geo_data().states


def get_all_states() -> list[StateUT]:
    """Return all 28 states (type == 'state')."""
    return [s for s in load_geo_data().states if s.type == "state"]


def get_all_uts() -> list[StateUT]:
    """Return all 8 union territories (type == 'ut')."""
    return [s for s in load_geo_data().states if s.type == "ut"]


def get_region_by_slug(slug: str) -> StateUT | None:
    """Find a state/UT by its slug.

    Args:
        slug: Kebab-case identifier (e.g. 'tamil-nadu').

    Returns:
        The matching StateUT, or None if not found.
    """
    for s in load_geo_data().states:
        if s.slug == slug:
            return s
    return None


def get_languages_for_region(slug: str) -> list[str]:
    """Return language codes for a region, defaulting to ['en'] if not found.

    Args:
        slug: Kebab-case identifier (e.g. 'tamil-nadu').

    Returns:
        List of language codes for the region.
    """
    region = get_region_by_slug(slug)
    if region is None:
        return ["en"]
    return list(region.languages)


def get_districts_for_region(slug: str) -> list[District]:
    """Return districts for a region, or an empty list if not found.

    Args:
        slug: Kebab-case identifier (e.g. 'tamil-nadu').

    Returns:
        List of District objects for the region.
    """
    region = get_region_by_slug(slug)
    if region is None:
        return []
    return list(region.districts)
