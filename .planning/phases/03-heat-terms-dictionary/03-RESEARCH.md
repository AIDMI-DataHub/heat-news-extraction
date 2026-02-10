# Phase 3: Heat Terms Dictionary - Research

**Researched:** 2026-02-10
**Domain:** Multilingual structured dictionary design, Indian language heat terminology, programmatic data modeling
**Confidence:** HIGH

## Summary

This phase transforms the existing heat terms research (`.planning/research/HEAT_TERMS_RESEARCH.md`, ~450+ terms across 14 languages and 8 categories) into a structured, programmatic dictionary that Phase 6 can consume for query generation. The research file already contains comprehensive native-script terms with category assignments, register classifications (formal/colloquial/borrowed), and confidence levels -- the work here is **structuring**, not **content creation**.

The monsoon project (`monsoon-news-extraction/language_map.py`) provides a proven pattern: a Python module with a function (`get_climate_impact_terms(language_code)`) that returns a flat list of terms per language. However, the heat pipeline needs significantly more structure: 8 categories per language, register metadata (formal vs. colloquial vs. borrowed), and the ability to programmatically filter terms by category for query generation. A flat list approach would lose valuable metadata that enables smarter query construction in Phase 6.

The recommended approach is a **JSON data file + Pydantic validation + Python query API** -- the same pattern already established for geographic data in Phase 2 (`india_geo.json` + `geo_loader.py`). This gives us: structured data editable without code changes, Pydantic validation at load time, cached access via `lru_cache`, and a clean function-based API for Phase 6 to consume.

**Primary recommendation:** Create `src/data/heat_terms.json` as the structured data file and `src/data/heat_terms_loader.py` as the Pydantic-validated loader with query functions. Follow the exact same architecture pattern as `geo_loader.py`. Populate from the existing HEAT_TERMS_RESEARCH.md content.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.10.6 | Data validation of the terms dictionary at load time | Already installed; same pattern as geo_loader.py |
| json (stdlib) | stdlib | Load terms from JSON file | Same pattern as india_geo.json loading |
| pathlib (stdlib) | stdlib | Resolve data file path | Same pattern as geo_loader.py |
| functools.lru_cache (stdlib) | stdlib | Cache loaded terms data | Same pattern as geo_loader.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing (stdlib) | stdlib | Type aliases for category/register literals | Constraining valid category and register values |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON data file | Python dict literal in .py file | JSON is the pattern already established for geo data; keeps data separate from code; editable by non-developers |
| JSON data file | YAML/TOML | Would add a new dependency (PyYAML); JSON is simpler and consistent with existing geo_loader |
| Pydantic models | Plain dict access | Loses validation at load time; Pydantic catches missing fields, bad categories, etc. |
| Single JSON file | Separate JSON per language | Single file is simpler, consistent with india_geo.json pattern; 450 terms is not large |

**Installation:**
No additional packages needed. All requirements already satisfied by Phase 1's `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
src/
  data/
    __init__.py              # Re-exports (add heat_terms functions)
    india_geo.json           # Existing geographic data
    geo_loader.py            # Existing geographic loader
    heat_terms.json          # NEW: Structured heat terms dictionary
    heat_terms_loader.py     # NEW: Pydantic-validated loader + query API
```

### Pattern 1: JSON Data Structure for Terms

**What:** A structured JSON file organizing terms by language > category, with metadata per term.
**When to use:** The single source of truth for all heat-related search terminology.
**Confidence:** HIGH -- follows established project patterns.

```json
{
  "version": "1.0.0",
  "languages": {
    "en": {
      "name": "English",
      "categories": {
        "heatwave": {
          "terms": [
            { "term": "heatwave", "register": "formal" },
            { "term": "heat wave", "register": "formal" },
            { "term": "severe heatwave", "register": "formal" },
            { "term": "scorching heat", "register": "journalistic" },
            { "term": "loo", "register": "colloquial" }
          ]
        },
        "death_stroke": {
          "terms": [
            { "term": "heatstroke", "register": "formal" },
            { "term": "sunstroke", "register": "colloquial" },
            { "term": "heat-related death", "register": "formal" }
          ]
        }
      }
    },
    "hi": {
      "name": "Hindi",
      "categories": {
        "heatwave": {
          "terms": [
            { "term": "\u0932\u0942", "register": "colloquial" },
            { "term": "\u0939\u0940\u091f \u0935\u0947\u0935", "register": "borrowed" },
            { "term": "\u092d\u0940\u0937\u0923 \u0917\u0930\u094d\u092e\u0940", "register": "journalistic" },
            { "term": "\u0909\u0937\u094d\u0923 \u0932\u0939\u0930", "register": "formal" }
          ]
        }
      }
    }
  }
}
```

**Key structural decisions:**
- Top-level keyed by ISO 639-1 language codes (same 14 as `SUPPORTED_LANGUAGES` in geo_loader.py)
- 8 categories as snake_case keys: `heatwave`, `death_stroke`, `water_crisis`, `power_cuts`, `crop_damage`, `human_impact`, `government_response`, `temperature`
- Each term carries a `register` field: `"formal"`, `"colloquial"`, `"journalistic"`, or `"borrowed"`
- Borrowed English terms appear in each regional language's category (e.g., Hindi heatwave category includes "हीट वेव")
- Version field allows future schema evolution

### Pattern 2: Pydantic Loader with Cached Query API (Same as geo_loader.py)

**What:** Pydantic models validate the JSON at load time; `lru_cache` ensures single read; query functions provide clean API.
**When to use:** For loading and querying heat terms data.
**Confidence:** HIGH -- mirrors verified geo_loader.py pattern.

```python
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

_DATA_DIR = Path(__file__).parent

# Valid categories and registers
TermCategory = Literal[
    "heatwave", "death_stroke", "water_crisis", "power_cuts",
    "crop_damage", "human_impact", "government_response", "temperature"
]
TermRegister = Literal["formal", "colloquial", "journalistic", "borrowed"]

TERM_CATEGORIES: frozenset[str] = frozenset({
    "heatwave", "death_stroke", "water_crisis", "power_cuts",
    "crop_damage", "human_impact", "government_response", "temperature"
})

class HeatTerm(BaseModel):
    model_config = ConfigDict(frozen=True)
    term: str = Field(..., min_length=1)
    register: TermRegister

class CategoryTerms(BaseModel):
    model_config = ConfigDict(frozen=True)
    terms: list[HeatTerm] = Field(min_length=1)

class LanguageTerms(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    categories: dict[TermCategory, CategoryTerms]

    @field_validator("categories")
    @classmethod
    def all_categories_present(cls, v):
        missing = TERM_CATEGORIES - set(v.keys())
        if missing:
            raise ValueError(f"Missing categories: {sorted(missing)}")
        return v

class HeatTermsDictionary(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str
    languages: dict[str, LanguageTerms]

@lru_cache(maxsize=1)
def load_heat_terms() -> HeatTermsDictionary:
    data_path = _DATA_DIR / "heat_terms.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return HeatTermsDictionary.model_validate(raw)

# Query functions
def get_terms_for_language(lang: str) -> list[str]:
    """All terms for a language, flattened across categories."""
    ...

def get_terms_by_category(lang: str, category: TermCategory) -> list[str]:
    """Terms for a specific language and category."""
    ...

def get_borrowed_terms(lang: str) -> list[str]:
    """Only borrowed English terms for a language."""
    ...

def get_all_languages() -> list[str]:
    """All language codes in the dictionary."""
    ...
```

### Pattern 3: Borrowed English Terms Injection

**What:** Every regional language's term set includes common borrowed English terms that appear in that script.
**When to use:** Ensuring search queries capture articles that mix native and English terminology.
**Confidence:** HIGH -- well-documented in HEAT_TERMS_RESEARCH.md cross-language patterns section.

The research documents these as universal across all 14 languages:
- "heat wave" / "heatwave" (transliterated in each script)
- "heat stroke" (transliterated in each script)
- "load shedding" (transliterated in each script)
- "red alert" / "orange alert" / "yellow alert" (transliterated in each script)
- "heat action plan" (primarily Hindi, Marathi, Gujarati)

These MUST be included as `register: "borrowed"` entries in every regional language's term set.

### Anti-Patterns to Avoid

- **Flat list without categories:** The monsoon project uses flat lists (`get_climate_impact_terms` returns a plain list). This loses category information needed for smarter query generation in Phase 6. Use structured data.
- **Romanized terms instead of native script:** All terms MUST be stored in native script (Devanagari, Tamil, Telugu, Bengali, etc.), not romanized. Romanized terms will not match news articles in native script. The research file already has all terms in native script.
- **Hardcoding terms in Python code:** Terms should live in JSON, not as Python dict literals. This makes the dictionary editable, diffable, and consumable by other tools without importing Python.
- **Over-engineering the schema:** The term metadata should be minimal (term + register). Adding confidence levels, source citations, or transliterations to the JSON would bloat the data without serving Phase 6's query generation needs. Keep the research-level metadata in the research doc only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON validation | Manual dict traversal with try/except | Pydantic model_validate | Pydantic catches schema violations at load time with clear error messages |
| Category completeness check | Manual loop checking 8 categories per language | Pydantic field_validator | Declarative validation is more maintainable and self-documenting |
| File path resolution | Hardcoded paths or os.path.join | `Path(__file__).parent` | Works regardless of working directory; established pattern in geo_loader.py |
| Data caching | Global variable or module-level loading | `lru_cache(maxsize=1)` | Thread-safe, lazy loading, established pattern in geo_loader.py |

**Key insight:** This phase is primarily a data curation task, not a library integration task. The code structure is a direct copy of the geo_loader.py pattern. The real work is transforming ~450 terms from the markdown research file into valid structured JSON.

## Common Pitfalls

### Pitfall 1: Unicode/Encoding Errors in JSON
**What goes wrong:** Native-script terms in JSON files get corrupted or cause encoding errors when reading/writing.
**Why it happens:** JSON files saved without explicit UTF-8 encoding, or editors that mangle non-Latin characters, or `json.loads` without `encoding="utf-8"` on the file read.
**How to avoid:** Always use `encoding="utf-8"` when reading the JSON file (as geo_loader.py already does). Verify the JSON file is saved as UTF-8. Include native-script terms directly (not as Unicode escape sequences like `\u0932\u0942`) for human readability.
**Warning signs:** Terms appear as `????` or `\uXXXX` in output; Pydantic validation passes but queries return no results.

### Pitfall 2: Missing Categories for Some Languages
**What goes wrong:** Some languages have fewer terms in the research file, leading to empty or missing categories.
**Why it happens:** Less-resourced languages (Assamese, Nepali) have fewer documented terms than Hindi or Tamil.
**How to avoid:** The Pydantic `field_validator` on `categories` should enforce all 8 categories are present for every language. For languages with sparse coverage in a category, include at minimum the borrowed English terms (which exist for all categories) plus any native terms available.
**Warning signs:** Pydantic validation error at load time listing missing categories.

### Pitfall 3: Duplicate Terms Across Categories
**What goes wrong:** Some terms legitimately span multiple categories (e.g., "loo" appears in both heatwave and death/stroke contexts).
**Why it happens:** Indian heat terminology has overlapping meanings -- "loo lagna" is both a heatwave descriptor and a heatstroke event.
**How to avoid:** Allow deliberate duplication across categories. The same term appearing in both `heatwave` and `death_stroke` categories is correct and desirable for maximum recall. Do NOT deduplicate across categories.
**Warning signs:** Artificially reduced term counts after deduplication.

### Pitfall 4: Forgetting Script-Specific Borrowed Terms
**What goes wrong:** Borrowed English terms are included only in Latin script, not transliterated into the target language's script.
**Why it happens:** "heat wave" in English is different from "हीट वेव" in Devanagari script -- the latter is what appears in Hindi news articles.
**How to avoid:** Borrowed terms MUST be in the target language's script. "Heat wave" for Hindi = "हीट वेव" (Devanagari), for Tamil = "ஹீட் வேவ்" (Tamil script), etc. The research file already has all these transliterations.
**Warning signs:** Search queries with Latin-script borrowed terms in regional language searches returning no results.

### Pitfall 5: Treating All Terms as Equal Priority
**What goes wrong:** Phase 6 query generation uses all 30+ terms per language, creating excessively long queries that hit API limits.
**Why it happens:** No mechanism to distinguish high-priority terms from supplementary ones.
**How to avoid:** The `register` field enables prioritization: `formal` and `colloquial` terms are highest priority (most commonly used in news), `journalistic` are medium, and `borrowed` are supplementary. Phase 6 can use this to build tiered queries.
**Warning signs:** Query strings exceeding API limits; too many API calls per language.

## Code Examples

Verified patterns from the existing codebase:

### Loading Pattern (from geo_loader.py -- proven)
```python
# Source: /Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/data/geo_loader.py
_DATA_DIR = Path(__file__).parent

@lru_cache(maxsize=1)
def load_geo_data() -> GeoData:
    data_path = _DATA_DIR / "india_geo.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    return GeoData.model_validate(raw)
```

The heat_terms_loader.py should follow this exact pattern.

### Query Function Pattern (from geo_loader.py -- proven)
```python
# Source: /Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/data/geo_loader.py
def get_languages_for_region(slug: str) -> list[str]:
    region = get_region_by_slug(slug)
    if region is None:
        return ["en"]
    return list(region.languages)
```

Heat terms query functions should follow this same pattern of delegating to the cached loader.

### Monsoon Terms Pattern (reference from older project -- NOT recommended to copy directly)
```python
# Source: /Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/language_map.py
# This shows the flat-list approach. Phase 3 should use structured data instead.
def get_climate_impact_terms(language_code: str) -> list:
    terms = {
        "en": ["monsoon", "heavy rain", "cloudburst", "flood", ...],
        "hi": ["मॉनसून", "भारी बारिश", "बादल फटना", "बाढ़", ...],
    }
    return terms.get(language_code, terms["en"])
```

This flat-list pattern loses category information. The heat pipeline should use structured JSON + query functions instead, but the API surface (a function taking a language code and returning terms) should be similar for ergonomics.

### Re-export Pattern (from src/data/__init__.py -- proven)
```python
# Source: /Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/data/__init__.py
from .geo_loader import (
    District, GeoData, StateUT,
    get_all_regions, get_all_states, get_all_uts,
    get_districts_for_region, get_languages_for_region,
    get_region_by_slug, load_geo_data,
)
```

The `__init__.py` should be updated to also re-export heat terms functions.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat term lists in Python dicts (monsoon project) | Structured JSON with Pydantic validation | This project (Phase 3) | Enables category-aware query generation, validated data |
| Romanized search terms | Native-script terms | This project (Phase 3) | Required for matching actual regional language news content |
| English-only queries across all languages | Language-specific + borrowed English terms | This project (Phase 3) | Dramatically improves regional language news coverage |

**Key evolution from monsoon project:**
- Monsoon project: ~30 terms per language in flat lists, no category structure, no register metadata
- Heat project: ~30-55 terms per language, 8 categories, register metadata (formal/colloquial/journalistic/borrowed)
- This additional structure enables Phase 6 to generate smarter, targeted queries rather than dumping all terms into one query string

## Data Inventory

### What Exists (from HEAT_TERMS_RESEARCH.md)

The research file contains **~450+ terms** across all 14 languages, already in native script, with:
- Category assignments (8 categories per language)
- Register classifications (formal/IMD, colloquial, journalistic, borrowed English)
- Confidence levels (HIGH/MEDIUM/LOW -- not needed in the JSON, research-level detail)
- Transliterations (not needed in the JSON -- for human reference only)
- Source attributions (not needed in the JSON)

**Coverage by language:**

| Language | Code | Approx Terms | All 8 Categories | Borrowed Terms | Status |
|----------|------|-------------|-------------------|----------------|--------|
| English | en | 35+ | Yes | N/A | Complete |
| Hindi | hi | 55+ | Yes | 10 | Complete |
| Tamil | ta | 35+ | Yes | 5 | Complete |
| Telugu | te | 35+ | Yes | 7 | Complete |
| Bengali | bn | 35+ | Yes | 6 | Complete |
| Marathi | mr | 35+ | Yes | 6 | Complete |
| Gujarati | gu | 30+ | Yes | 7 | Complete |
| Kannada | kn | 25+ | Yes | 5 | Complete |
| Malayalam | ml | 25+ | Yes | 5 | Complete |
| Odia | or | 25+ | Yes | 3 | Complete |
| Punjabi | pa | 25+ | Yes | 5 | Complete |
| Assamese | as | 22+ | Yes | 3 | Complete |
| Urdu | ur | 30+ | Yes | 7 | Complete |
| Nepali | ne | 25+ | Yes | 3 | Complete |

### Notable Regional-Specific Terms

These must not be lost in the structuring process:
- **Tamil:** "அக்னி நட்சத்திரம்" (agni nakshatram) -- culturally unique term for the hottest astronomical period
- **Marathi:** "भारनियमन" (bhaarniyaman) -- official Maharashtra state term for load shedding/power cuts
- **Bengali:** "দাবদাহ" (dabdaho) -- THE classic Bengali term for scorching heat
- **Telugu:** "వడ గాలులు" (vada gaalulu) -- THE classic Telugu term for hot winds
- **Hindi:** "लू" (loo) -- the single most important colloquial heat term across North India

### Cross-Language Patterns to Preserve

1. **The "loo" family:** Present in 9 languages (hi, mr, bn, or, gu, pa, ur, ne, as) with language-specific verb forms
2. **"Mercury rising" idiom:** Present in 7 languages -- journalistic register, temperature category
3. **Borrowed English universals:** "heat wave", "heat stroke", "load shedding", "red alert" present in all 14 languages

## Open Questions

1. **Should LOW confidence terms from the research file be included?**
   - What we know: The research file marks some terms as LOW confidence ("inferred from linguistic patterns, needs verification")
   - What's unclear: Whether including unverified terms helps recall or adds noise
   - Recommendation: Include them. The phase description says "HIGH RECALL over high precision -- better to capture noise than miss coverage." LOW confidence terms are still valid search terms; they just might generate fewer results. No harm in including them.

2. **Should the JSON include region-specific annotations?**
   - What we know: Some terms are region-specific (e.g., "भारनियमन" only in Maharashtra, "অক্নি নক্ষত্রম" only in Tamil Nadu)
   - What's unclear: Whether Phase 6 needs to know which regions a term applies to
   - Recommendation: Do NOT add region annotations in Phase 3. The dictionary is keyed by language, and language already maps to regions via `india_geo.json`. Region-specific filtering can be added later if needed. Keep the schema simple.

3. **How should the "death/stroke" category be named in JSON?**
   - What we know: The research file uses "death/stroke" but JSON keys should be valid identifiers
   - What's unclear: Best snake_case convention
   - Recommendation: Use `"death_stroke"` as the JSON key. Clear, valid, and maps to the research document's intent.

## Integration Points

### Upstream Dependencies (Phase 2 -- already complete)
- `SUPPORTED_LANGUAGES` frozenset in `geo_loader.py` defines the 14 valid language codes -- heat terms must use exactly these codes
- `india_geo.json` maps regions to languages -- Phase 6 will combine both data sources

### Downstream Consumers (Phase 6 -- query generation)
Phase 6 will use the heat terms dictionary to generate search queries by:
1. Looking up a region's languages from `geo_loader.py`
2. For each language, getting terms from `heat_terms_loader.py`
3. Combining terms with location names (district/state) to form search queries

The API must support:
- Get all terms for a language (for broad queries)
- Get terms by category (for targeted category-specific queries)
- Get borrowed terms only (to supplement native-language queries)
- Get terms by register (to prioritize formal/colloquial for first-pass queries)

## Sources

### Primary (HIGH confidence)
- `/Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/.planning/research/HEAT_TERMS_RESEARCH.md` -- comprehensive terms data (450+ terms, 14 languages, 8 categories)
- `/Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/data/geo_loader.py` -- proven loader pattern to replicate
- `/Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/data/india_geo.json` -- proven JSON data pattern to replicate
- `/Users/akashyadav/Desktop/AIDMI/Github/heat-news-extraction/src/models/article.py` -- language code constraint pattern

### Secondary (MEDIUM confidence)
- `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/language_map.py` -- working multilingual terms pattern (flat list approach)
- `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/monsoon.py` -- how terms are consumed for query generation

### Tertiary (LOW confidence)
- None. All findings are based on direct examination of existing codebase and research documents.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; exact same stack as Phase 2
- Architecture: HIGH -- direct replication of geo_loader.py pattern (proven, verified)
- Data content: HIGH -- all terms already exist in HEAT_TERMS_RESEARCH.md in native script
- Pitfalls: HIGH -- identified from actual monsoon project experience and Unicode handling knowledge

**Research date:** 2026-02-10
**Valid until:** Indefinite (no external library changes involved; this is internal data structuring)
