# Phase 2: Data Models and Geographic Data - Research

**Researched:** 2026-02-10
**Domain:** Pydantic v2 data modeling, Indian geographic/administrative data, IST timezone handling
**Confidence:** HIGH

## Summary

This phase requires two distinct deliverables: (1) a Pydantic v2 Article model with typed fields and IST timezone-aware date validation, and (2) a comprehensive geographic master data file mapping all 36 Indian states/UTs and their ~787 districts to relevant languages.

The Pydantic v2 stack is well-suited for both. Pydantic v2.10.6 (already installed) provides `AwareDatetime` for enforcing timezone-aware datetimes, `field_validator` for custom IST enforcement, and `model_config` via `ConfigDict` for controlling validation/serialization behavior. Python 3.12's built-in `zoneinfo` module provides `ZoneInfo("Asia/Kolkata")` for IST without any third-party dependency.

The geographic data challenge is substantial but solvable. The existing monsoon pipeline's `language_map.py` already has all 36 states/UTs with multilingual mappings -- this is the verified source of truth for state-to-language relationships. District data (787 districts as of March 2025) needs to be assembled from external sources. The `sab99r/Indian-States-And-Districts` GitHub repo provides a structured JSON file with 743 districts (slightly outdated) that can be used as a starting baseline, but the planner should note that the exact count fluctuates (787-800+ depending on recent administrative changes) and perfectionism here is counterproductive -- having ~770+ districts is sufficient for news query coverage.

**Primary recommendation:** Use Pydantic v2 `AwareDatetime` with a custom `field_validator` to enforce IST (UTC+05:30) timezone on all dates. Store geographic data as a single JSON file in `src/data/` with a Pydantic model for loading/validation. Reuse the monsoon pipeline's state/language mappings as the authoritative source for language associations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.10.6 | Data modeling, validation, serialization | Already installed; provides AwareDatetime, field_validator, ConfigDict |
| Python zoneinfo | stdlib (3.12) | IST timezone handling via ZoneInfo("Asia/Kolkata") | Built-in, no dependency; IANA timezone database |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | stdlib | Load/dump geographic master data | Loading the states/districts JSON at startup |
| pathlib (stdlib) | stdlib | File path handling for data files | Resolving data file paths relative to package |
| enum (stdlib) | stdlib | Language code and source type enumerations | Type-safe language codes, source identifiers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| zoneinfo | pytz | pytz is legacy; zoneinfo is stdlib in Python 3.9+; no reason to add pytz |
| JSON file for geo data | Python dict literal in .py file | JSON is editable by non-developers, parseable by other tools; .py is harder to validate/update |
| JSON file for geo data | SQLite database | Overkill for ~800 read-only records loaded once at startup |

**Installation:**
No additional packages needed. All requirements are already satisfied by Phase 1's `requirements.txt` (pydantic==2.10.6) plus Python 3.12 stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/
  models/
    __init__.py          # Re-exports Article, ArticleRef, etc.
    article.py           # Article Pydantic model with all fields
    geographic.py        # State, District, GeoRegistry Pydantic models
  data/
    __init__.py          # Package marker
    india_geo.json       # Master geographic data file
    geo_loader.py        # Functions to load and query geographic data
```

### Pattern 1: Pydantic v2 Model with AwareDatetime and IST Validation
**What:** Use `AwareDatetime` as the field type to enforce timezone presence, then use a `field_validator` to normalize/verify the timezone is IST (Asia/Kolkata, UTC+05:30).
**When to use:** For the Article model's `date` field.
**Example:**
```python
# Source: Pydantic v2.10 official docs (AwareDatetime) + zoneinfo stdlib
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

IST = ZoneInfo("Asia/Kolkata")
IST_OFFSET = timedelta(hours=5, minutes=30)

class Article(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    date: AwareDatetime
    language: str = Field(..., min_length=2, max_length=3)
    state: str = Field(..., min_length=1)
    district: str | None = None
    full_text: str | None = None
    search_term: str = Field(..., min_length=1)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("date")
    @classmethod
    def ensure_ist_timezone(cls, v: datetime) -> datetime:
        """Convert any timezone-aware datetime to IST."""
        return v.astimezone(IST)
```

### Pattern 2: Geographic Data as Validated Pydantic Models
**What:** Define Pydantic models for State/UT and District entries, load from JSON, validate at startup.
**When to use:** For the geographic master data loading.
**Example:**
```python
# Source: Pydantic v2.10 official docs (BaseModel, ConfigDict)
from pydantic import BaseModel, ConfigDict, Field

class District(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    slug: str  # kebab-case for URL/query use

class StateUT(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    slug: str  # e.g., "tamil-nadu"
    type: str  # "state" or "ut"
    languages: list[str]  # e.g., ["ta", "en"]
    districts: list[District]
```

### Pattern 3: Centralized GeoRegistry for Lookup
**What:** A singleton/module-level registry that loads the JSON once and provides lookup methods.
**When to use:** Any time the pipeline needs to look up states, districts, or language mappings.
**Example:**
```python
import json
from pathlib import Path
from functools import lru_cache

_DATA_DIR = Path(__file__).parent

@lru_cache(maxsize=1)
def load_geo_data() -> list[StateUT]:
    """Load and validate all geographic data from JSON."""
    data_path = _DATA_DIR / "india_geo.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return [StateUT.model_validate(entry) for entry in raw["states"]]

def get_all_states() -> list[StateUT]:
    return [s for s in load_geo_data() if s.type == "state"]

def get_all_uts() -> list[StateUT]:
    return [s for s in load_geo_data() if s.type == "ut"]

def get_languages_for_region(slug: str) -> list[str]:
    for entry in load_geo_data():
        if entry.slug == slug:
            return entry.languages
    return ["en"]
```

### Anti-Patterns to Avoid
- **Raw dicts/lists for articles:** The monsoon pipeline uses `list[str]` positional indexing (`entry[0]` = title, `entry[2]` = date). This is exactly what DATA-01 prohibits. Use typed Pydantic models.
- **Hardcoded state lists in multiple files:** The monsoon pipeline duplicates the state list in `monsoon.py`, `utils.py`, and `language_map.py`. Use a single JSON source of truth.
- **pytz for timezone handling:** The monsoon pipeline uses `pytz.timezone('Asia/Kolkata')`. Python 3.12 has `zoneinfo` built-in; use `ZoneInfo("Asia/Kolkata")` instead.
- **Naive datetimes converted to IST later:** Always store as timezone-aware from the start. The Article model should reject naive datetimes via `AwareDatetime`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timezone-aware datetime validation | Custom regex parsing of ISO strings | Pydantic `AwareDatetime` + `field_validator` | Pydantic handles ISO 8601, RFC 3339, and offset parsing automatically |
| Date string parsing from news sources | Manual strptime with format guessing | Pydantic's built-in datetime coercion + `BeforeValidator` for edge cases | Pydantic parses most common formats; only add a before-validator for truly exotic formats |
| JSON schema validation for geo data | Manual key-checking of loaded JSON | Pydantic `model_validate()` on the loaded JSON | Catches missing/wrong-typed fields automatically with clear error messages |
| Slug generation (kebab-case) | Custom string replacement logic | Pre-compute slugs in the JSON data file | Slugs are static data, not runtime computation |

**Key insight:** Pydantic v2 does the heavy lifting for both validation and serialization. The Article model and the geographic data models should both lean on Pydantic's built-in type coercion and validators rather than writing custom parsing logic.

## Common Pitfalls

### Pitfall 1: AwareDatetime Accepts Any Timezone, Not Just IST
**What goes wrong:** Using `AwareDatetime` alone accepts UTC, EST, or any timezone. Articles from RSS feeds typically come in UTC/GMT. Without conversion, dates stored in the model will have mixed timezones.
**Why it happens:** `AwareDatetime` only checks that `tzinfo` is not None -- it does not constrain WHICH timezone.
**How to avoid:** Add a `field_validator` on the `date` field that calls `.astimezone(IST)` to normalize all incoming datetimes to IST.
**Warning signs:** Tests pass with UTC datetimes but later phases see inconsistent timezone offsets in output.

### Pitfall 2: Naive Datetime Strings Without Timezone Info
**What goes wrong:** Some news sources return dates like "2026-02-10 14:30:00" (no timezone). Pydantic `AwareDatetime` will reject these, causing validation failures that crash the pipeline.
**Why it happens:** Google News RSS returns GMT/UTC but some scraped dates have no timezone info.
**How to avoid:** Use a `BeforeValidator` or `field_validator(mode='before')` that detects naive datetime strings and attaches IST timezone before Pydantic's core validation runs.
**Warning signs:** `ValidationError` with type `timezone_aware` during article ingestion.

### Pitfall 3: District Count Instability
**What goes wrong:** Searching for an exact count (e.g., "exactly 770 districts") and finding it doesn't match any source. India's district count changes as states reorganize administratively.
**Why it happens:** New districts are carved out regularly. Sources disagree: 743 (sab99r GitHub), 787 (mudranidhi.com as of March 2025), 800+ (other 2025 sources).
**How to avoid:** Use the sab99r/Indian-States-And-Districts JSON as a solid baseline (743 districts covering all 36 states/UTs). Add a note in the data file that the count is approximate. Do NOT block on getting an exact number.
**Warning signs:** Spending hours trying to reconcile different district lists.

### Pitfall 4: Language Code Mismatch Between Monsoon Pipeline and Heat Pipeline
**What goes wrong:** The monsoon pipeline uses "mni" (Manipuri/Meitei) and "lus" (Mizo) which are NOT in the heat pipeline's 14 supported languages (en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne).
**Why it happens:** The heat pipeline explicitly scopes to 14 languages. Manipur and Mizoram in the monsoon pipeline map to codes outside this set.
**How to avoid:** When adapting the monsoon pipeline's `multilingual_mapping`, replace "mni" with available codes (e.g., ["en", "hi"]) and "lus" with ["en", "hi"]. The 14 supported languages are: en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne.
**Warning signs:** Validation failures if the Article model constrains `language` to the 14-code set.

### Pitfall 5: Frozen Model Prevents Post-Creation Updates
**What goes wrong:** Setting `frozen=True` on the Article model (recommended for data integrity) means you cannot set `full_text` after initial creation since extraction happens later.
**Why it happens:** Articles are created from RSS/API results first (no full text), then full text is extracted in Phase 7.
**How to avoid:** Either (a) make `full_text` not frozen by using a separate model stage (ArticleRef -> Article), or (b) use `model_copy(update={...})` to create a new instance with the full text, or (c) don't use `frozen=True` at all. Recommendation: use two models -- `ArticleRef` (from search, no full_text) and `Article` (complete, with full_text).
**Warning signs:** `ValidationError: Instance is frozen` when trying to set `full_text` after construction.

### Pitfall 6: Geographic Data File Not Found at Runtime
**What goes wrong:** Loading `india_geo.json` using relative paths breaks depending on the working directory when running `python main.py`.
**Why it happens:** Relative paths depend on CWD, not on the Python package location.
**How to avoid:** Use `Path(__file__).parent / "india_geo.json"` to resolve relative to the module file, not the CWD.
**Warning signs:** `FileNotFoundError` when running from a different directory.

## Code Examples

Verified patterns from official sources:

### AwareDatetime Field with IST Normalization
```python
# Source: https://docs.pydantic.dev/2.10/api/types/ (AwareDatetime)
# + Python 3.12 zoneinfo stdlib
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import AwareDatetime, BaseModel, Field, field_validator

IST = ZoneInfo("Asia/Kolkata")

class Article(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: str
    source: str
    date: AwareDatetime
    language: str = Field(..., pattern=r"^(en|hi|ta|te|bn|mr|gu|kn|ml|or|pa|as|ur|ne)$")
    state: str
    district: str | None = None
    full_text: str | None = None
    search_term: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("date")
    @classmethod
    def normalize_to_ist(cls, v: datetime) -> datetime:
        """Normalize all timezone-aware datetimes to IST (Asia/Kolkata)."""
        return v.astimezone(IST)
```

### Handling Naive Datetime Input with BeforeValidator
```python
# Source: https://docs.pydantic.dev/2.10/concepts/validators/
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
from pydantic import BeforeValidator
from typing_extensions import Annotated

IST = ZoneInfo("Asia/Kolkata")

def coerce_naive_to_ist(value: Any) -> Any:
    """If a naive datetime is provided, assume it is IST."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value

ISTDatetime = Annotated[datetime, BeforeValidator(coerce_naive_to_ist)]
# Use ISTDatetime as the type annotation in place of AwareDatetime
# if you need to accept naive datetimes from some sources.
```

### Loading and Validating Geographic JSON Data
```python
# Source: Pydantic v2 model_validate pattern
import json
from pathlib import Path
from pydantic import BaseModel

class District(BaseModel):
    name: str
    slug: str

class StateUT(BaseModel):
    name: str
    slug: str
    type: str  # "state" | "ut"
    languages: list[str]
    districts: list[District]

class GeoData(BaseModel):
    states: list[StateUT]

def load_geo_data() -> GeoData:
    data_path = Path(__file__).parent / "india_geo.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return GeoData.model_validate(raw)
```

### Geographic JSON Data File Format
```json
{
  "states": [
    {
      "name": "Tamil Nadu",
      "slug": "tamil-nadu",
      "type": "state",
      "languages": ["ta", "en"],
      "districts": [
        {"name": "Chennai", "slug": "chennai"},
        {"name": "Coimbatore", "slug": "coimbatore"}
      ]
    },
    {
      "name": "Delhi",
      "slug": "delhi",
      "type": "ut",
      "languages": ["hi", "en", "ur", "pa"],
      "districts": [
        {"name": "Central Delhi", "slug": "central-delhi"},
        {"name": "New Delhi", "slug": "new-delhi"}
      ]
    }
  ]
}
```

### Two-Stage Model Pattern (ArticleRef -> Article)
```python
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

class ArticleRef(BaseModel):
    """Lightweight reference from search results (no full text yet)."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1)
    url: str
    source: str
    date: AwareDatetime
    language: str
    state: str
    district: str | None = None
    search_term: str

    @field_validator("date")
    @classmethod
    def normalize_to_ist(cls, v):
        return v.astimezone(IST)

class Article(ArticleRef):
    """Complete article with extracted full text and scoring."""
    full_text: str | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytz for timezones | `zoneinfo` (stdlib) | Python 3.9 (2020) | No dependency needed; IANA database built-in |
| Pydantic v1 `validator` decorator | Pydantic v2 `field_validator` + `model_validator` | Pydantic v2 (2023) | Different API; `@classmethod` required; `mode` parameter |
| Pydantic v1 `class Config:` | Pydantic v2 `model_config = ConfigDict(...)` | Pydantic v2 (2023) | No inner class; use `ConfigDict` import |
| `dict()` / `.json()` methods | `.model_dump()` / `.model_dump_json()` | Pydantic v2 (2023) | Old methods deprecated |
| Manual datetime string parsing | `AwareDatetime` / `NaiveDatetime` type hints | Pydantic v2 (2023) | Built-in timezone-aware/naive enforcement |

**Deprecated/outdated:**
- `pytz`: Still works but `zoneinfo` is the stdlib replacement. Do not add pytz as a dependency.
- Pydantic v1 API patterns: The project uses v2.10.6; use v2 patterns exclusively.

## Existing Reference Data Analysis

### Monsoon Pipeline's language_map.py (HIGH confidence)
**Location:** `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/language_map.py`

The monsoon pipeline provides verified, production-tested mappings:
- **28 states** with slug names (kebab-case): andhra-pradesh through west-bengal
- **8 union territories**: andaman-and-nicobar-islands, chandigarh, dadra-and-nagar-haveli-and-daman-and-diu, lakshadweep, delhi, puducherry, jammu-and-kashmir, ladakh
- **Multilingual mappings** via `get_all_languages_for_region()`: Each state/UT maps to 2-4 language codes

**Key adaptation needed for heat pipeline:**
- Remove "mni" (Meitei/Manipuri) -- not in the 14 supported languages. Replace Manipur's mapping with `["en", "hi"]`
- Remove "lus" (Mizo) -- not in the 14 supported languages. Replace Mizoram's mapping with `["en", "hi"]`
- The remaining 14 language codes (en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne) align perfectly with the heat pipeline's scope

### District Data: sab99r/Indian-States-And-Districts (MEDIUM confidence)
**Source:** https://github.com/sab99r/Indian-States-And-Districts
**Format:** JSON with 36 state/UT entries, 743 total districts
**Schema:** `{"states": [{"state": "Name", "districts": ["Dist1", "Dist2", ...]}]}`

This provides a solid baseline but:
- Count is 743, not 787 (the latest as of March 2025). Missing ~44 recently created districts.
- Names are in English display form, not slug form. Slugs must be generated.
- Does not include language mappings (those come from the monsoon pipeline).
- Some state names may not match the monsoon pipeline's slug format (e.g., "Andaman and Nicobar Islands" vs "andaman-and-nicobar-islands").

**Recommendation:** Use this as the starting district list. The ~44 missing districts will not meaningfully impact news coverage since those areas will still be covered by their parent state queries. Generate slugs programmatically from names.

### State-wise District Counts (as of March 2025, MEDIUM confidence)
Source: mudranidhi.com

| State/UT | Districts | State/UT | Districts |
|----------|-----------|----------|-----------|
| Andhra Pradesh | 26 | Arunachal Pradesh | 27 |
| Assam | 35 | Bihar | 38 |
| Chhattisgarh | 33 | Goa | 2 |
| Gujarat | 33 | Haryana | 22 |
| Himachal Pradesh | 12 | Jharkhand | 24 |
| Karnataka | 31 | Kerala | 14 |
| Madhya Pradesh | 55 | Maharashtra | 36 |
| Manipur | 16 | Meghalaya | 12 |
| Mizoram | 11 | Nagaland | 16 |
| Odisha | 30 | Punjab | 23 |
| Rajasthan | 50 | Sikkim | 6 |
| Tamil Nadu | 38 | Telangana | 33 |
| Tripura | 8 | Uttar Pradesh | 75 |
| Uttarakhand | 13 | West Bengal | 23 |
| Andaman & Nicobar | 3 | Chandigarh | 1 |
| DNH & DD | 3 | Delhi | 11 |
| Jammu & Kashmir | 20 | Lakshadweep | 1 |
| Ladakh | 2 | Puducherry | 4 |
| **Total** | **787** | | |

## Open Questions

1. **Exact district list vs. baseline approach**
   - What we know: The sab99r GitHub JSON has 743 districts. March 2025 count is 787. The exact list fluctuates.
   - What's unclear: Whether the 44 "missing" districts significantly impact news coverage.
   - Recommendation: Start with sab99r's 743-district dataset. The missing districts are newly created and their news will still be captured by parent state queries. Note: the exact count is not a blocking concern.

2. **Should ArticleRef and Article be separate models?**
   - What we know: Articles are created from search results (no full_text), then enriched later (Phase 7) with full text extraction. Using `frozen=True` would prevent mutation.
   - What's unclear: Whether the pipeline will need to modify articles in-place or can use immutable model_copy.
   - Recommendation: Use two models (ArticleRef and Article) where Article inherits from ArticleRef and adds `full_text` and `relevance_score`. Both are frozen. Use `model_copy(update={...})` or construct Article from ArticleRef data.

3. **Where should india_geo.json live?**
   - What we know: It needs to be loadable relative to the Python package, not CWD.
   - What's unclear: Whether `src/data/` is the best location or if it should be at project root.
   - Recommendation: Place in `src/data/india_geo.json` and load via `Path(__file__).parent`. This keeps it within the package structure and works regardless of CWD.

## Sources

### Primary (HIGH confidence)
- **Pydantic v2.10 docs** - AwareDatetime type, field_validator patterns, ConfigDict: https://docs.pydantic.dev/2.10/api/types/
- **Pydantic v2.10 docs** - Validators (field_validator, model_validator, BeforeValidator): https://docs.pydantic.dev/2.10/concepts/validators/
- **Pydantic v2.10 docs** - Models (BaseModel, ConfigDict, model_dump): https://docs.pydantic.dev/2.10/concepts/models/
- **Python 3.12 zoneinfo** - IANA timezone support: https://docs.python.org/3/library/zoneinfo.html
- **Monsoon pipeline language_map.py** - State/UT/language mappings (verified, production-tested): `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/language_map.py`

### Secondary (MEDIUM confidence)
- **sab99r/Indian-States-And-Districts** - District JSON data (743 districts): https://github.com/sab99r/Indian-States-And-Districts
- **mudranidhi.com** - State-wise district counts (787 total, March 2025): https://www.mudranidhi.com/districts-in-india/
- **Pydantic GitHub discussions** - AwareDatetime usage patterns: https://github.com/pydantic/pydantic/discussions/4700

### Tertiary (LOW confidence)
- **District count precision** - Sources disagree on exact count (743-800+). The exact number is a moving target and should not be a blocker.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pydantic v2.10.6 is installed and verified; zoneinfo is stdlib; all patterns confirmed via official docs
- Architecture: HIGH - Two-model pattern (ArticleRef/Article) is standard Pydantic; geo data as JSON + model_validate is well-documented
- Geographic data: MEDIUM - State/UT list is definitive (36); district list is approximate (743-787); language mappings are verified from monsoon pipeline
- Pitfalls: HIGH - All pitfalls identified from actual codebase analysis (monsoon pipeline patterns) and official Pydantic docs

**Research date:** 2026-02-10
**Valid until:** 2026-03-10 (30 days -- Pydantic v2.10 and geographic data are stable)
