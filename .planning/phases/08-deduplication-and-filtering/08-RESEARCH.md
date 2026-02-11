# Phase 8: Deduplication and Filtering - Research

**Researched:** 2026-02-11
**Domain:** URL normalization, fuzzy string matching, keyword-based relevance scoring, multilingual text processing
**Confidence:** HIGH

## Summary

Phase 8 takes the list of `Article` objects (with `full_text` populated by Phase 7) and applies two sequential transformations: deduplication (removing duplicate articles collected from overlapping queries/sources) and relevance filtering (scoring each article for genuine heat/disaster relevance and excluding clearly irrelevant content). The pipeline's core value is **high recall over high precision** -- borderline articles must be kept.

The deduplication challenge has two layers: (1) URL-level dedup where the same article was collected through different queries but has the same underlying URL (after stripping tracking parameters), and (2) title-level dedup where the same news story was published by different outlets with similar titles, or the same article was returned by different API sources (Google News, NewsData.io, GNews) with slightly different URLs. URL dedup is straightforward with stdlib `urllib.parse`. Title dedup across 14 languages (including Devanagari, Tamil, Telugu, Bengali, etc.) requires a character-level similarity metric; Python's stdlib `difflib.SequenceMatcher` handles Unicode natively and requires no dependencies. For the expected article counts (hundreds, not millions), SequenceMatcher's O(n^2) pairwise comparison is fast enough. When duplicates are found, the "higher-quality" version is kept (longer `full_text`, more metadata fields populated).

The relevance filtering challenge is to separate genuine heat/disaster impact articles from noise that matches search terms but is not actually about heat events. The pipeline already has 934 heat terms across 14 languages and 10 categories (from `heat_terms.json`). The filtering approach should be rules-based (no ML dependencies): check how many heat terms appear in the title and full_text, check which categories are represented, and apply negative signals from a configurable exclusion pattern list (cricket scores, generic weather forecasts, summer fashion, etc.). Articles score 0.0-1.0 on the `relevance_score` field. The threshold for exclusion should be very low (e.g., articles scoring below 0.1 are excluded) to maintain high recall.

**Primary recommendation:** Use stdlib only for URL normalization (`urllib.parse`) and title similarity (`difflib.SequenceMatcher`). Keep the relevance scorer simple: term presence counting with category diversity bonus, negative signals from a JSON-configurable exclusion list. No external dependencies needed. All models are frozen, so dedup/filter functions must return new lists of Article objects (potentially with updated `relevance_score`).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| urllib.parse (stdlib) | stdlib | URL parsing, query parameter stripping, normalization | Zero dependencies; handles all URL schemes; `urlparse` + `urlencode` + `urlunparse` is the standard Python URL manipulation pattern |
| difflib (stdlib) | stdlib | `SequenceMatcher.ratio()` for title similarity scoring | Zero dependencies; works on any Unicode string including Devanagari, Tamil, Telugu; adequate performance for hundreds of articles |
| re (stdlib) | stdlib | Regex-based pattern matching for exclusion patterns | Zero dependencies; compiled regex for fast multi-pattern matching against article text |
| json (stdlib) | stdlib | Loading configurable exclusion patterns from JSON file | Zero dependencies; consistent with existing `heat_terms.json` loading pattern |
| pydantic | 2.10.6 | Article model with `relevance_score` field | Already installed; frozen models require creating new Article instances with updated scores |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | stdlib | Dedup/filter operation logging | Log dedup counts, filter decisions, score distributions |
| src.data.heat_terms_loader | (internal) | Access to 934 heat terms across 14 languages, 10 categories | Used by relevance scorer to check term presence in article text |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| difflib.SequenceMatcher | rapidfuzz 3.14.3 | 40x faster, but adds a C dependency (compiled wheels needed); SequenceMatcher is fast enough for hundreds of articles -- would need rapidfuzz only if processing 10,000+ titles |
| difflib.SequenceMatcher | url-normalize 2.2.1 for URLs | url-normalize has `filter_params=True` for automatic tracking param removal, but adds a dependency for something achievable with 15 lines of stdlib code |
| Simple term counting | scikit-learn TF-IDF | Massive dependency for a simple keyword presence check; overkill when we already have a curated term dictionary |
| JSON exclusion config | YAML config | Adds PyYAML dependency; JSON is consistent with existing `heat_terms.json` pattern; no YAML files exist in the project |

**Installation:**
No additional packages needed. All requirements are already satisfied by the existing `requirements.txt`. Phase 8 uses only Python stdlib plus already-installed pydantic.

## Architecture Patterns

### Recommended Project Structure
```
src/
  dedup/
    __init__.py           # Re-exports deduplicate_articles, filter_articles
    _url_dedup.py         # URL normalization and URL-based deduplication
    _title_dedup.py       # Title similarity deduplication
    _relevance.py         # Relevance scoring and filtering
  data/
    exclusion_patterns.json  # Configurable irrelevant pattern list (FILT-03)
```

### Pattern 1: Functional Pipeline Stage (list[Article] -> list[Article])
**What:** Each dedup/filter function takes a list of Articles and returns a new (smaller or re-scored) list. No mutation. No side effects beyond logging.
**When to use:** Every dedup and filter stage.
**Why:** Articles are frozen Pydantic models. The pipeline is a sequence of transformations. Each stage is independently testable.
**Example:**
```python
def deduplicate_by_url(articles: list[Article]) -> list[Article]:
    """Remove articles with duplicate normalized URLs, keeping higher-quality version."""
    seen: dict[str, Article] = {}
    for article in articles:
        norm_url = normalize_url(article.url)
        if norm_url in seen:
            existing = seen[norm_url]
            if _quality_score(article) > _quality_score(existing):
                seen[norm_url] = article
        else:
            seen[norm_url] = article
    return list(seen.values())
```

### Pattern 2: URL Normalization with stdlib
**What:** Parse URL, strip tracking parameters, normalize scheme/host/path, reconstruct.
**When to use:** Before comparing URLs for deduplication.
**Example:**
```python
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

# Tracking parameters to strip (DEDU-01)
_TRACKING_PARAMS: frozenset[str] = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "fbclid", "gclid", "yclid", "msclkid",
    "_ga", "_gl", "ref", "source", "mkt_tok", "mc_cid", "mc_eid",
    "hsCtaTracking", "si", "__cft__", "__tn__",
})

def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication comparison."""
    parsed = urlparse(url)
    # Lowercase scheme and host
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    # Remove www. prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # Strip tracking params
    params = parse_qs(parsed.query, keep_blank_values=False)
    clean_params = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
    # Sort params for consistent comparison
    sorted_query = urlencode(clean_params, doseq=True)
    # Remove trailing slash from path
    path = parsed.path.rstrip("/") or "/"
    # Remove fragment
    return urlunparse((scheme, netloc, path, "", sorted_query, ""))
```

### Pattern 3: Title Similarity with SequenceMatcher
**What:** Compare article titles using character-level similarity. Works across all scripts (Latin, Devanagari, Tamil, etc.) because SequenceMatcher operates on Unicode code points.
**When to use:** After URL dedup, to catch cross-source/cross-query duplicates with different URLs but same content.
**Example:**
```python
from difflib import SequenceMatcher

def _title_similarity(title_a: str, title_b: str) -> float:
    """Compute title similarity ratio (0.0 to 1.0)."""
    # Normalize: lowercase (for Latin), strip whitespace
    a = title_a.strip().lower()
    b = title_b.strip().lower()
    return SequenceMatcher(None, a, b).ratio()

def deduplicate_by_title(
    articles: list[Article],
    threshold: float = 0.85,
) -> list[Article]:
    """Remove articles with highly similar titles, keeping higher-quality version."""
    kept: list[Article] = []
    for article in articles:
        is_dup = False
        for i, existing in enumerate(kept):
            if _title_similarity(article.title, existing.title) >= threshold:
                # Found a duplicate -- keep the higher-quality one
                if _quality_score(article) > _quality_score(existing):
                    kept[i] = article
                is_dup = True
                break
        if not is_dup:
            kept.append(article)
    return kept
```

### Pattern 4: Quality Scoring for Duplicate Resolution (DEDU-03)
**What:** When two articles are duplicates, keep the one with better data quality. Score based on: full_text length, metadata completeness, and source priority.
**When to use:** In both URL and title dedup when choosing which version to keep.
**Example:**
```python
def _quality_score(article: Article) -> int:
    """Score article data quality for duplicate resolution.

    Higher score = better quality. Used to decide which duplicate to keep.
    """
    score = 0
    # Full text quality (most important)
    if article.full_text is not None:
        score += 100 + len(article.full_text)  # Longer text = more complete extraction
    # Metadata completeness
    if article.district is not None:
        score += 10  # Has district-level geo info
    if article.source != "Unknown":
        score += 5   # Has identified source
    return score
```

### Pattern 5: Relevance Scoring with Term Presence + Category Diversity (FILT-01, FILT-02)
**What:** Score each article's relevance to heat/disaster events by checking how many heat terms appear in its title and full_text, across how many categories. A "heatstroke death in Rajasthan" article will match terms from multiple categories (health + weather + governance), while a cricket score article mentioning "heat" will match at most one.
**When to use:** After deduplication, before output.
**Example:**
```python
def score_relevance(article: Article) -> float:
    """Score article relevance from 0.0 to 1.0."""
    text = _combine_text(article)  # title + full_text, lowered
    if not text:
        return 0.0  # No text to score

    terms = get_terms_for_language(article.language)
    matched_terms: set[str] = set()
    matched_categories: set[str] = set()

    for cat in TERM_CATEGORIES:
        cat_terms = get_terms_by_category(article.language, cat)
        for term in cat_terms:
            if term.lower() in text:
                matched_terms.add(term)
                matched_categories.add(cat)

    if not matched_terms:
        return 0.0

    # Base score: term match density (capped)
    term_score = min(len(matched_terms) / 3.0, 1.0)  # 3+ terms = full score
    # Category diversity bonus (multi-category = more likely relevant)
    category_score = min(len(matched_categories) / 2.0, 1.0)  # 2+ categories = full score
    # Title match bonus (terms in title are stronger signal)
    title_terms = sum(1 for t in matched_terms if t.lower() in article.title.lower())
    title_bonus = 0.2 if title_terms > 0 else 0.0

    raw_score = (term_score * 0.5) + (category_score * 0.3) + title_bonus
    return min(raw_score, 1.0)
```

### Pattern 6: Configurable Exclusion Patterns (FILT-03)
**What:** A JSON file containing regex patterns for clearly irrelevant content. Loaded at runtime, checked against article title + text. Can be updated without code changes.
**When to use:** As a negative signal in relevance scoring, or as a hard exclusion for very low-relevance content.
**Example exclusion_patterns.json:**
```json
{
  "version": "1.0.0",
  "description": "Patterns that indicate clearly irrelevant content. Updated without code changes.",
  "patterns": [
    {"pattern": "\\bcricket\\b.*\\bscore\\b", "category": "sports", "description": "Cricket match scores"},
    {"pattern": "\\bIPL\\b.*\\b(match|final|semi)\\b", "category": "sports", "description": "IPL cricket"},
    {"pattern": "\\bweather\\s+forecast\\b.*\\b(tomorrow|week|today)\\b", "category": "weather_forecast", "description": "Generic weather forecasts"},
    {"pattern": "\\bsummer\\s+(fashion|style|recipe|vacation|getaway)\\b", "category": "lifestyle", "description": "Summer lifestyle content"},
    {"pattern": "\\bhoroscope\\b", "category": "astrology", "description": "Horoscope/astrology content"},
    {"pattern": "\\b(hot|heat)\\s+(deal|sale|offer|discount)\\b", "category": "marketing", "description": "Marketing using heat terminology"}
  ]
}
```

### Pattern 7: Frozen Model Update for relevance_score
**What:** Since Article is frozen, setting `relevance_score` requires creating a new Article instance. Use `model_copy(update=...)` which is Pydantic v2's way to create a modified copy of a frozen model.
**When to use:** When the relevance scorer assigns scores to articles.
**Example:**
```python
# Pydantic v2 frozen model update pattern
scored_article = article.model_copy(update={"relevance_score": 0.85})
```
**Note:** `model_copy(update=...)` is the Pydantic v2 replacement for the v1 `.copy(update=...)`. It creates a new instance with the specified fields changed, respecting `frozen=True`. This is more efficient than `Article(**article.model_dump(), relevance_score=new_score)` because it avoids re-validating all fields.

### Anti-Patterns to Avoid
- **Mutating Article.relevance_score directly:** Article has `frozen=True`. Any attempt to set attributes raises `ValidationError`. Use `model_copy(update=...)`.
- **Adding ML/embedding dependencies for title dedup:** The project has no numpy, scikit-learn, or sentence-transformers. Adding them for a few hundred articles is massive dependency bloat. SequenceMatcher is sufficient.
- **Strict filtering that drops borderline articles:** The core value is high recall. The filter should only exclude articles that are clearly irrelevant (cricket scores, horoscopes, marketing). When in doubt, keep the article.
- **URL dedup before Phase 7 extraction:** URL dedup must happen AFTER extraction because Google News URLs are resolved to actual URLs in Phase 7. The `ArticleRef.url` field from Google News contains `news.google.com` redirect URLs, but after extraction, we know the actual URLs.
- **Normalizing cross-language titles for comparison:** Don't try to translate or transliterate Hindi titles to compare with English titles. Cross-language duplicate detection via title similarity is not reliable and not required -- the same article in Hindi and English are different articles worth keeping. Title dedup should only compare articles in the same language.
- **Using O(n^2) title comparison without language bucketing:** Compare titles only within the same language group. A Hindi article title will never be similar to a Tamil article title, so comparing across languages is wasted computation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL parsing and manipulation | Custom regex URL parser | `urllib.parse.urlparse()` + `parse_qs()` + `urlunparse()` | stdlib handles edge cases (ports, auth, fragments, encoded characters) correctly |
| String similarity scoring | Custom edit distance calculation | `difflib.SequenceMatcher.ratio()` | Ratcliff/Obershelp algorithm handles Unicode natively; tested implementation in stdlib |
| Regex compilation and caching | Manual regex compilation loop | `re.compile()` with module-level constants or `@lru_cache` | re module already caches compiled patterns; explicit compile for clarity |
| JSON config loading with validation | Custom config parser | `json.loads()` + Pydantic model validation | Consistent with existing `heat_terms_loader.py` pattern |
| Frozen model field update | `Article(**article.model_dump(), relevance_score=x)` | `article.model_copy(update={"relevance_score": x})` | `model_copy` skips re-validation of unchanged fields; more efficient and idiomatic Pydantic v2 |

**Key insight:** Phase 8 requires zero new dependencies. The dedup problem at this scale (hundreds of articles, not millions) is solvable with Python stdlib. The relevance scoring problem is solvable with the existing heat terms dictionary. The temptation to add ML-based dedup (embeddings, cosine similarity) or NLP-based relevance scoring (transformers, spaCy) is strong but unnecessary and violates the project's lightweight dependency philosophy.

## Common Pitfalls

### Pitfall 1: Google News URLs Not Yet Resolved at Dedup Time
**What goes wrong:** Attempting URL dedup on `ArticleRef` objects (pre-extraction) where Google News articles still have `news.google.com/rss/articles/...` redirect URLs. Two different articles from Google News would have unique redirect URLs even if they point to the same actual article.
**Why it happens:** The URL resolution happens in Phase 7 `_resolver.py`. Phase 8 must operate on the post-extraction `Article` list.
**How to avoid:** Phase 8 dedup operates on `list[Article]` (post-extraction), not `list[ArticleRef]`. However, note that `Article.url` still contains the original `ArticleRef.url` (the Google News redirect URL), NOT the resolved URL. The resolver does not update the model's url field -- it only uses the resolved URL internally for fetching HTML.
**Warning signs:** URL dedup fails to catch obvious duplicates from Google News.
**Critical implication:** Since the resolved URL is not stored on the Article model, URL dedup on Google News articles requires a different strategy. Two options: (a) store the resolved URL in the model (requires Phase 2 model change), or (b) accept that URL dedup only works for NewsData.io and GNews articles (which have actual URLs), and rely on title dedup to catch Google News duplicates. **Option (b) is recommended** given the frozen model constraint and the fact that title dedup will catch these cases.

### Pitfall 2: SequenceMatcher Too Slow for Large Collections
**What goes wrong:** O(n^2) pairwise title comparison becomes slow when article count exceeds ~5,000.
**Why it happens:** SequenceMatcher.ratio() is relatively slow (Python-level character comparison). With 500 articles * 500 comparisons = 250,000 comparisons, each taking ~0.1ms = ~25 seconds. With 5,000 articles = 25,000,000 comparisons = impractical.
**How to avoid:** Bucket articles by language before comparison (Hindi titles vs Hindi titles only). This typically reduces the problem from N^2 to k*(N/k)^2 where k is the number of languages. With 14 languages, this is a 14x speedup. For expected volumes (hundreds of articles), this is more than sufficient.
**Warning signs:** Dedup phase taking more than 30 seconds for a typical run.

### Pitfall 3: Overly Aggressive Filtering Kills Recall
**What goes wrong:** Setting the relevance threshold too high drops articles that mention heat impacts in passing but are genuinely about heat events (e.g., an article about "water crisis in Chennai" that doesn't use the word "heatwave" but describes a heat-related water shortage).
**Why it happens:** Keyword-based scoring misses semantic relevance. An article about heat impacts may use synonyms, descriptions, or context not captured in the term dictionary.
**How to avoid:** Set an extremely low exclusion threshold (e.g., score < 0.05 or 0.1). Only exclude articles that match zero heat terms AND match an exclusion pattern. The principle is: if the article was found by a heat-term search query, it is probably relevant. The default should be "keep" unless there is strong evidence of irrelevance.
**Warning signs:** Manual review shows relevant articles being filtered out; precision is prioritized over recall.

### Pitfall 4: Exclusion Patterns Too Broad
**What goes wrong:** A pattern like `\bcricket\b` matches "cricket" anywhere, including legitimate articles like "Cricket ground used as heat shelter in Delhi" (a genuinely relevant article about heat response).
**Why it happens:** Simple keyword patterns lack context. The pattern should look for cricket in combination with irrelevance indicators (scores, match, innings), not cricket alone.
**How to avoid:** Exclusion patterns should be conjunctive (match pattern AND lack of heat indicators) rather than disjunctive. Each pattern should be specific enough that it only matches clearly irrelevant content. Test patterns against edge cases before deploying.
**Warning signs:** Articles about heat shelters in sports venues, heat-related construction worker deaths at cricket stadiums, or power outages during cricket matches being filtered out.

### Pitfall 5: Title Similarity Threshold Too Low or Too High
**What goes wrong:** Threshold too low (0.6): Different articles about the same topic are incorrectly merged. Threshold too high (0.95): Near-identical titles with minor differences (different source attribution suffix) are not caught.
**Why it happens:** The optimal threshold depends on title format. Google News often appends " - Publisher Name" to titles. The same article from different sources may have titles like "Heatwave kills 10 in Rajasthan - Times of India" vs "Heatwave kills 10 in Rajasthan - NDTV". These are the same article, different source attributions.
**How to avoid:** Strip the source attribution suffix (text after the last " - ") before comparison. Use a threshold of 0.85 for the stripped title. This catches substantive duplicates while preserving genuinely different articles.
**Warning signs:** Running dedup on test data and manually checking: are duplicates being missed? Are non-duplicates being merged?

### Pitfall 6: Ignoring Articles with full_text=None in Relevance Scoring
**What goes wrong:** Articles where text extraction failed (`full_text=None`) get relevance_score=0.0 and are filtered out, even though their titles clearly indicate heat relevance.
**Why it happens:** The scorer only checks full_text for term matches. If extraction failed, there's no text to match.
**How to avoid:** Score the title separately as a fallback. If full_text is None but the title contains heat terms, assign a moderate base score (e.g., 0.3-0.5). These articles were found by heat-term search queries, so their titles likely contain heat terms. The principle: extraction failure should not cause article exclusion.
**Warning signs:** Many articles with `full_text=None` being filtered out despite heat-relevant titles.

## Code Examples

Verified patterns from official sources and codebase analysis:

### URL Normalization with stdlib
```python
# Source: Python 3.14 urllib.parse docs
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_TRACKING_PARAMS: frozenset[str] = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "fbclid", "gclid", "yclid", "msclkid",
    "_ga", "_gl", "ref", "source", "mkt_tok", "mc_cid", "mc_eid",
})

def normalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase, strip tracking params, sort query."""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    # Strip tracking params, sort remaining
    params = parse_qs(parsed.query, keep_blank_values=False)
    clean = {k: sorted(v) for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
    query = urlencode(clean, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))
```

### Title Similarity with SequenceMatcher
```python
# Source: Python 3.14 difflib docs
from difflib import SequenceMatcher

def title_similarity(title_a: str, title_b: str) -> float:
    """Compute similarity ratio between two titles.

    Works with any Unicode script (Latin, Devanagari, Tamil, etc.)
    because SequenceMatcher operates on Unicode code points.
    """
    a = title_a.strip().lower()
    b = title_b.strip().lower()
    return SequenceMatcher(None, a, b).ratio()

# Example: same article from different sources
title_similarity(
    "Heatwave kills 10 in Rajasthan - Times of India",
    "Heatwave kills 10 in Rajasthan - NDTV"
)  # ~0.87

# Example: Hindi titles
title_similarity(
    "राजस्थान में भीषण गर्मी से 10 की मौत - दैनिक जागरण",
    "राजस्थान में भीषण गर्मी से 10 की मौत - नवभारत टाइम्स"
)  # ~0.85
```

### Frozen Model Update with model_copy
```python
# Source: Pydantic v2 docs (model_copy with update)
from src.models.article import Article

# Article is frozen -- cannot mutate fields
# Use model_copy to create a new instance with updated relevance_score
scored = article.model_copy(update={"relevance_score": 0.85})
# scored is a NEW Article instance; original is unchanged
```

### Loading Exclusion Patterns from JSON
```python
# Source: Pattern consistent with src/data/heat_terms_loader.py
import json
import re
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@lru_cache(maxsize=1)
def load_exclusion_patterns() -> list[re.Pattern[str]]:
    """Load and compile exclusion patterns from JSON config."""
    path = _DATA_DIR / "exclusion_patterns.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        re.compile(entry["pattern"], re.IGNORECASE)
        for entry in raw["patterns"]
    ]
```

### Complete Dedup + Filter Pipeline Stage
```python
# Shows how the three stages compose
def deduplicate_and_filter(articles: list[Article]) -> list[Article]:
    """Full Phase 8 pipeline: URL dedup -> title dedup -> score -> filter."""
    # Stage 1: URL deduplication
    deduped_url = deduplicate_by_url(articles)
    logger.info("URL dedup: %d -> %d articles", len(articles), len(deduped_url))

    # Stage 2: Title deduplication (per language bucket)
    deduped_title = deduplicate_by_title(deduped_url, threshold=0.85)
    logger.info("Title dedup: %d -> %d articles", len(deduped_url), len(deduped_title))

    # Stage 3: Relevance scoring
    scored = [
        article.model_copy(update={"relevance_score": score_relevance(article)})
        for article in deduped_title
    ]

    # Stage 4: Filter (very low threshold -- high recall)
    exclusion_patterns = load_exclusion_patterns()
    filtered = [
        a for a in scored
        if a.relevance_score >= 0.05 or not _matches_exclusion(a, exclusion_patterns)
    ]
    logger.info(
        "Relevance filter: %d -> %d articles (excluded %d)",
        len(scored), len(filtered), len(scored) - len(filtered),
    )

    return filtered
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Exact URL string match for dedup | URL normalization (strip tracking params, lowercase, sort query params) | Ongoing best practice | Catches duplicates with different tracking parameters from different sources |
| TF-IDF / embedding-based dedup | Character-level similarity (SequenceMatcher/rapidfuzz) for title dedup | N/A (scale-dependent) | At hundreds of articles, character similarity is sufficient and dependency-free; embedding-based approaches needed only at 100K+ scale |
| ML-based relevance classification | Rules-based keyword scoring with configurable exclusion patterns | N/A (domain-specific) | For a curated domain with 934 known terms, rule-based scoring is transparent, debuggable, and requires no training data |
| Hardcoded exclusion rules | JSON-configurable exclusion patterns | Best practice | Allows domain experts to update patterns without code changes; critical for evolving false-positive landscape |

**Deprecated/outdated:**
- `fuzzywuzzy`: Superseded by `rapidfuzz` (MIT license, faster, actively maintained); but neither is needed when SequenceMatcher suffices
- `newspaper3k/newspaper4k` keyword extraction: Would add a heavy dependency; the existing heat_terms dictionary is more targeted than generic keyword extraction

## Important Codebase Observations

### Resolved URL Not Stored on Article Model
The `_resolver.py` in Phase 7 resolves Google News redirect URLs internally but does NOT update the `Article.url` field. The `Article.url` still contains the original `ArticleRef.url` (which for Google News is `https://news.google.com/rss/articles/...`). This means:
- URL-based dedup will NOT catch Google News duplicates (all Google News URLs are unique redirect URLs)
- URL-based dedup WILL work for NewsData.io and GNews articles (they store actual article URLs)
- Title-based dedup is the primary dedup mechanism for Google News articles

### Article Inherits ArticleRef (Frozen)
`Article` extends `ArticleRef` with `full_text` and `relevance_score`. Both have `frozen=True`. To update `relevance_score`, use `article.model_copy(update={"relevance_score": new_score})`.

### Heat Terms Already Available via Cached Loader
`src/data/heat_terms_loader.py` provides:
- `get_terms_for_language(lang)` -- all terms for a language (flattened)
- `get_terms_by_category(lang, category)` -- terms for a specific category
- `TERM_CATEGORIES` -- frozenset of all 10 category names
- Data is cached via `@lru_cache` -- safe to call repeatedly

### Same Article from Multiple Queries
The pipeline generates multiple queries per state-language-source combination (8 categories for Google News, 1 broad query for NewsData/GNews). The same article can appear in results for multiple category queries. After extraction, these will be `Article` objects with identical URLs (for non-Google sources) or identical titles (for all sources). This is the primary source of duplicates.

## Open Questions

1. **Should the resolved URL be stored on the Article model?**
   - What we know: Phase 7's `_resolver.py` resolves Google News redirect URLs but only uses them internally for HTTP fetching. The `Article.url` field retains the original Google News redirect URL.
   - What's unclear: Whether adding a `resolved_url` field to Article would break the frozen model constraint or require a Phase 2 model change.
   - Recommendation: Do NOT add a field. Use `model_copy(update={"url": resolved_url})` in the extractor if needed, but this is a Phase 7 concern. For Phase 8, rely on title dedup for Google News articles. This approach is simpler and avoids cross-phase changes.

2. **What is the optimal title similarity threshold?**
   - What we know: NewsCatcher uses 0.97 for titles (with Levenshtein). SequenceMatcher uses a different algorithm (Ratcliff/Obershelp). A threshold of 0.85 after stripping source attribution should catch most duplicates.
   - What's unclear: The actual distribution of title similarities in the pipeline's output. The threshold may need tuning based on real data.
   - Recommendation: Start with 0.85 after stripping " - Source Name" suffixes. Log all near-threshold decisions (0.80-0.90 range) for manual review during initial testing.

3. **How should articles with full_text=None be handled in relevance scoring?**
   - What we know: Some articles will have `full_text=None` due to extraction failures (blocked sites, timeouts). These articles still have titles that were found by heat-term queries.
   - What's unclear: What percentage of articles will have no full_text, and whether title-only scoring is sufficient.
   - Recommendation: Score title-only articles with a baseline score of 0.3 if any heat term appears in the title. Do not filter them out -- extraction failure should not cause data loss. The downstream consumer (Phase 9 output) can flag these as "title-only" entries.

4. **Should dedup consider the `search_term` field?**
   - What we know: Each ArticleRef has a `search_term` field recording which heat term query found it. The same URL found by different search terms is still the same article.
   - What's unclear: Whether to preserve the `search_term` from the higher-quality version or somehow merge search terms.
   - Recommendation: Keep the `search_term` from whichever duplicate is kept (the higher-quality version). Do not try to merge search terms -- the field is informational, not functional.

## Sources

### Primary (HIGH confidence)
- **Python 3.14 urllib.parse docs** - URL parsing, parse_qs, urlencode, urlunparse: https://docs.python.org/3/library/urllib.parse.html
- **Python 3.14 difflib docs** - SequenceMatcher, ratio(), get_close_matches: https://docs.python.org/3/library/difflib.html
- **Pydantic v2 docs** - model_copy(update=...) for frozen model field updates: https://docs.pydantic.dev/latest/
- **Existing codebase** - `src/models/article.py` (Article model, frozen=True), `src/extraction/_extractor.py` (extraction flow, relevance_score=0.0), `src/data/heat_terms_loader.py` (934 terms, 14 languages, 10 categories), `src/extraction/_resolver.py` (URL resolution, resolved URL not stored)

### Secondary (MEDIUM confidence)
- **url-normalize 2.2.1 on PyPI** - filter_params feature for tracking parameter removal (alternative to stdlib approach): https://pypi.org/project/url-normalize/
- **RapidFuzz 3.14.3** - Fast fuzzy string matching (alternative to SequenceMatcher if performance insufficient): https://pypi.org/project/RapidFuzz/
- **NewsCatcher deduplication docs** - Industrial dedup approach (0.95 cosine similarity, 0.97 Levenshtein for titles): https://www.newscatcherapi.com/docs/v3/documentation/guides-and-concepts/articles-deduplication
- **CPython issue #106865** - SequenceMatcher performance characteristics and limitations: https://github.com/python/cpython/issues/106865

### Tertiary (LOW confidence)
- **SequenceMatcher on non-Latin scripts** - No published benchmarks found for SequenceMatcher performance or accuracy on Devanagari/Tamil/Telugu text; algorithm is character-based so it should work, but accuracy of similarity scores for non-Latin scripts is unverified
- **Optimal title similarity threshold** - No published research found for news title dedup thresholds using Ratcliff/Obershelp algorithm; the 0.85 threshold is an informed estimate that requires validation on real pipeline output

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib; no dependencies to verify
- Architecture (dedup pipeline): HIGH - Functional transformation pattern matches existing codebase; frozen model handling verified via Pydantic v2 docs
- URL normalization: HIGH - stdlib urllib.parse is well-documented and battle-tested
- Title dedup with SequenceMatcher: MEDIUM - Algorithm works on Unicode, but optimal threshold for multilingual news titles needs empirical validation
- Relevance scoring: MEDIUM - Term presence counting is straightforward, but the scoring formula (weights, thresholds) needs tuning on real data
- Exclusion patterns: HIGH - JSON config pattern matches existing heat_terms.json approach
- Pitfalls: HIGH - Critical observation about resolved URLs not being stored on Article model verified by reading _extractor.py and _resolver.py source code

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days -- stdlib-only approach is stable; scoring thresholds may need adjustment after initial pipeline runs)
