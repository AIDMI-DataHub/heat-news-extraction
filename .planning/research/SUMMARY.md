# Research Synthesis: Heat News Extraction Pipeline

**Synthesized**: 2026-02-10
**Sources**: ANALYSIS.md (monsoon pipeline study), MCP_LANDSCAPE.md (tooling landscape), HEAT_TERMS_RESEARCH.md (multilingual terms)

---

## Executive Summary

Three parallel research tracks converge on a clear architecture: **Pure Python async pipeline with multi-source news APIs, trafilatura for article extraction, and 450+ heat terms across 14 Indian languages.** The monsoon pipeline's domain knowledge (state/language mappings, URL patterns, relevance filtering) is valuable; its infrastructure (Selenium, pygooglenews, sequential processing) must be replaced entirely.

---

## Key Finding #1: Multi-Source API Strategy (from MCP_LANDSCAPE.md)

**No single free API covers 800+ entities daily. Combine three sources:**

| Source | Daily Limit | Role | Coverage |
|--------|------------|------|----------|
| Google News RSS | ~600-800 (soft, rate-limited) | Primary workhorse | Best volume, 8+ Indian languages, no API key |
| NewsData.io | 200 credits/day | Secondary | State-level queries, 5+ Indian languages |
| GNews | 100 requests/day | Tertiary/failover | High-priority states, 7+ Indian languages |

**Total capacity: ~900-1,100 queries/day** with smart batching. Enough for 36 states (all 14 languages) + 300 active districts (3 key languages).

**Critical decision: NO MCP servers at runtime.** MCP is for interactive AI sessions, not batch pipelines. Direct Python API calls with httpx + feedparser.

## Key Finding #2: Reuse Domain Knowledge, Replace Infrastructure (from ANALYSIS.md)

**Reuse from monsoon pipeline:**
- State/UT → language mappings (language_map.py) — complete and correct
- URL date extraction patterns (9 formats for Indian news URLs)
- Content relevance filtering logic (term presence + context clues)
- Newspaper database CSV (curated Indian newspapers by state/language)
- Multi-layer deduplication approach (URL → content fingerprint → title)
- Script-based language detection

**Replace entirely:**
- pygooglenews (dead library; build thin feedparser wrapper)
- Selenium/Playwright for extraction (use trafilatura — 10x faster, no browser)
- Sequential processing (use async/parallel — 36 states simultaneously)
- Raw list data structures (use Pydantic models)
- No crash recovery (add checkpoint/resume)
- Pre-creating 13,505 empty directories (create on write)
- subprocess-based orchestration (single Python entry point)

## Key Finding #3: 450+ Heat Terms Across 14 Languages (from HEAT_TERMS_RESEARCH.md)

**Term coverage by language:**

| Language | Total Terms | HIGH Confidence | Key Unique Finding |
|----------|-------------|-----------------|-------------------|
| English | 35+ | 28 | IMD official terminology (red/orange/yellow alert) |
| Hindi | 55+ | 40 | "लू" (loo) is THE dominant colloquial term |
| Tamil | 35+ | 25 | "அக்னி நட்சத்திரம்" (agni nakshatram) — culturally unique fire-star period |
| Telugu | 35+ | 25 | "ఎండ దెబ్బ" (enda debba, "sun blow") — standard heatstroke term |
| Bengali | 35+ | 25 | "দাবদাহ" (dabdaho) — dominant literary/journalistic term |
| Marathi | 35+ | 25 | "भारनियमन" (bharaniyaman) — Maharashtra-specific power regulation term |
| Gujarati | 30+ | 22 | Standard terms track closely with Hindi |
| Kannada | 25+ | 20 | Good coverage of borrowed English terms |
| Malayalam | 25+ | 20 | "സൂര്യാഘാതം" (sooryaaghaatam) — formal sunstroke term |
| Odia | 25+ | 20 | Critical for heat death reporting (Odisha has highest heat deaths) |
| Punjabi | 25+ | 18 | Wheat crop damage terms essential (ਕਣਕ ਦੀ ਫ਼ਸਲ) |
| Assamese | 22+ | 16 | Smaller term set but covers all categories |
| Urdu | 30+ | 22 | Perso-Arabic vocabulary alongside Hindi-shared terms |
| Nepali | 25+ | 18 | Covers Sikkim/Darjeeling hill regions |

**Cross-language patterns discovered:**
1. "Loo" (लू/লু/ଲୁ/لو) family spans 9+ languages — single most important colloquial term
2. Borrowed English terms (heat wave, heat stroke, load shedding, red alert) appear in EVERY language — must include in queries
3. "Mercury rising" idiom used across 7 languages as headline pattern
4. Each language has 8 categories: heatwave, death/stroke, water crisis, power cuts, crop damage, human impact, government response, temperature

## Key Finding #4: The Math Works — Barely (from MCP_LANDSCAPE.md)

**Smart batching strategy:**
- State-level: 36 states × 5 key languages = 180 queries → Google News RSS
- State-level extended: 36 × 14 languages = 504 queries → Google News RSS
- District-level: ~300 active districts × 3 languages ÷ 5 districts/query = 180 queries → Google News RSS
- State-level supplement: 200 queries → NewsData.io
- Priority states: 100 queries → GNews
- **Total: ~900 queries needed, ~1,500+ capacity available**

**45-minute GitHub Actions constraint:**
- With 2-second delays: ~1,200 Google News requests fit in 40 minutes
- NewsData.io and GNews run in parallel (separate rate limits)
- Priority order: state-level first (guaranteed to complete), then districts
- Checkpoint/resume if pipeline doesn't finish

## Key Finding #5: Core Python Stack (from MCP_LANDSCAPE.md + ANALYSIS.md)

```
httpx          — async HTTP client (replaces requests + aiohttp)
feedparser     — Google News RSS parsing (replaces pygooglenews)
trafilatura    — article extraction (replaces newspaper3k + Selenium)
pydantic       — data models (replaces raw lists)
tenacity       — retry with exponential backoff
aiofiles       — async file I/O
```

**What to NOT use:**
- Any MCP server (batch pipeline, not interactive AI)
- Selenium/Playwright (too heavy for news articles)
- newspaper3k (abandoned; trafilatura is strictly better)
- pygooglenews (semi-maintained; trivial to replace)
- Firecrawl/Bright Data (not free)

---

## Architecture Direction

```
[Heat Terms Dictionary] ──> [Query Generator]
[State/District/Language Maps] ──┘     |
                                       v
                         [Multi-Source Search Layer]
                         |-- Google News RSS (httpx + feedparser)
                         |-- NewsData.io API (httpx)
                         |-- GNews API (httpx)
                                       |
                                       v
                         [URL Deduplication Layer]
                         |-- URL normalization
                         |-- Content fingerprinting
                         |-- Title similarity
                                       |
                                       v
                         [Article Extraction] -- trafilatura (primary)
                                       |
                                       v
                         [Storage] -- JSON + CSV output
                                   -- Checkpoint state (SQLite/JSON)
```

**Key design principles:**
1. **Async-first**: All I/O via httpx async — process states in parallel
2. **Source-agnostic interface**: Each source implements `search(query, lang, country) -> List[ArticleRef]`
3. **Hierarchical querying**: States first, then districts for states with results
4. **Crash recovery**: Checkpoint which queries completed; resume on restart
5. **Graceful degradation**: If one source fails, others cover the gap
6. **Pydantic models**: No more position-based indexing on raw lists

---

## Risks to Track

| Risk | Severity | Mitigation |
|------|----------|------------|
| Google News throttling from GitHub Actions IP | HIGH | Multi-source; polite crawling; adaptive delays |
| 45-minute GitHub Actions timeout | HIGH | Priority ordering; checkpoint/resume; state-level first |
| Indian regional sites blocking scrapers | MEDIUM | trafilatura handles most; realistic User-Agent headers |
| Heat terms missing actual journalism vocabulary | MEDIUM | Verification TODO list in HEAT_TERMS_RESEARCH.md; iterate after first runs |
| NewsData.io/GNews reduce free tiers | MEDIUM | Google News RSS can absorb; pipeline degrades gracefully |

---

## Verification Items Before Building

1. [ ] NewsData.io free tier: Still 200 credits/day? Which Indian languages supported?
2. [ ] GNews free tier: Still 100/day?
3. [ ] Google News RSS rate limiting from cloud IPs (GitHub Actions)
4. [ ] Currents API: Free tier limits and Indian language support — potential 4th source
5. [ ] Heat terms: Validate HIGH confidence terms against actual Google News results
6. [ ] trafilatura: Test against 10 Indian regional news sites (Dainik Jagran, Dinamalar, Eenadu, etc.)

---

*Synthesis complete. Ready for requirements definition and roadmap creation.*
