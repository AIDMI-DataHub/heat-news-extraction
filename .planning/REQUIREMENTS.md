# Requirements: Heat News Extraction Pipeline

**Defined:** 2026-02-10
**Core Value:** Capture every heat-related news report from every corner of India, in every language, every day -- high recall over high precision.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Collection

- [ ] **COLL-01**: Pipeline queries all 36 Indian states and union territories daily for heat-related news
- [ ] **COLL-02**: Pipeline queries ~770 districts using smart batching (multiple districts per query)
- [ ] **COLL-03**: Pipeline uses hierarchical querying -- states first, then districts for states with active heat news
- [ ] **COLL-04**: Pipeline searches Google News RSS as primary source (~600 queries/day)
- [ ] **COLL-05**: Pipeline searches NewsData.io API as secondary source (~200 queries/day)
- [ ] **COLL-06**: Pipeline searches GNews API as tertiary source (~100 queries/day)
- [ ] **COLL-07**: Each news source implements a common interface: search(query, language, country) -> List[ArticleRef]
- [ ] **COLL-08**: Pipeline distributes queries across sources using a rate-limit-aware scheduler

### Language

- [ ] **LANG-01**: Pipeline supports 14+ Indian languages: en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne
- [ ] **LANG-02**: Queries use native-script terms (not English translations) for each language
- [ ] **LANG-03**: Heat terms dictionary covers 8 categories per language: heatwave, death/stroke, water crisis, power cuts, crop damage, human impact, government response, temperature
- [ ] **LANG-04**: Dictionary includes both formal/IMD terms and colloquial/journalistic terms
- [ ] **LANG-05**: Dictionary includes borrowed English terms that appear in regional language news (heat wave, heat stroke, load shedding, red alert)

### Extraction

- [ ] **EXTR-01**: Pipeline extracts full article text from collected URLs using trafilatura
- [ ] **EXTR-02**: Article extraction handles Indian language scripts (Devanagari, Tamil, Telugu, Bengali, etc.) correctly
- [ ] **EXTR-03**: Failed extractions are logged but do not halt the pipeline

### Deduplication

- [ ] **DEDU-01**: Pipeline deduplicates articles by normalized URL (remove tracking params, resolve redirects)
- [ ] **DEDU-02**: Pipeline deduplicates articles by title similarity for cross-language/cross-query duplicates
- [ ] **DEDU-03**: When duplicates found, pipeline keeps the higher-quality version (longer text, more metadata)

### Filtering

- [ ] **FILT-01**: Pipeline filters for genuine heat/disaster relevance (not weather forecasts, cricket, or generic summer articles)
- [ ] **FILT-02**: Pipeline uses term presence + context indicators for relevance scoring
- [ ] **FILT-03**: Pipeline has an irrelevant pattern exclusion list (configurable)
- [ ] **FILT-04**: Filtering prioritizes high recall -- borderline articles are kept, not discarded

### Data Model

- [x] **DATA-01**: Articles use Pydantic models with typed fields (no raw lists or position-based indexing)
- [x] **DATA-02**: Article model includes: title, url, source, date (IST), language, state/district, full_text, search_term, relevance_score
- [x] **DATA-03**: All dates are validated and stored in ISO format with IST timezone

### Output

- [ ] **OUTP-01**: Pipeline outputs JSON files organized by date and state/UT
- [ ] **OUTP-02**: Pipeline outputs CSV files organized by date and state/UT
- [ ] **OUTP-03**: Output directories are created on write (not pre-created)
- [ ] **OUTP-04**: Output includes metadata: collection timestamp, sources queried, query terms used, articles found/extracted/filtered

### Reliability

- [ ] **RELI-01**: Pipeline saves checkpoint state after each completed query batch
- [ ] **RELI-02**: Pipeline can resume from last checkpoint on restart (skip completed queries)
- [ ] **RELI-03**: Each news source has independent circuit breaker (failure in one doesn't halt others)
- [ ] **RELI-04**: Pipeline uses exponential backoff with jitter for rate limit errors
- [ ] **RELI-05**: Pipeline completes state-level queries first (guaranteed minimum coverage) before district-level

### Automation

- [ ] **AUTO-01**: Pipeline runs daily via GitHub Actions workflow
- [ ] **AUTO-02**: Pipeline completes within 45-minute GitHub Actions timeout
- [ ] **AUTO-03**: Pipeline operates entirely on free tier (zero API cost)
- [ ] **AUTO-04**: GitHub Actions workflow commits collected data to the repository
- [ ] **AUTO-05**: Pipeline uses async I/O (httpx) to process multiple sources in parallel

### Infrastructure

- [ ] **INFR-01**: Single Python entry point (no subprocess orchestration)
- [ ] **INFR-02**: Core stack: httpx, feedparser, trafilatura, pydantic, tenacity, aiofiles
- [ ] **INFR-03**: No browser dependencies (no Selenium, no Playwright for production)
- [ ] **INFR-04**: Single requirements.txt with pinned versions
- [x] **INFR-05**: State/UT and district master list with language mappings as structured data

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Testing

- **TEST-01**: Unit tests for heat terms dictionary validation
- **TEST-02**: Integration tests for each news source adapter
- **TEST-03**: End-to-end test with mock API responses
- **TEST-04**: Benchmark extraction success rates per source

### Monitoring

- **MONR-01**: Daily summary report (articles collected, extraction rate, source health)
- **MONR-02**: Alerting when collection drops below threshold
- **MONR-03**: Historical trend tracking of collection volumes

### Direct RSS

- **DRSS-01**: Direct RSS feeds from curated Indian newspaper list
- **DRSS-02**: Newspaper database CSV as supplementary data source

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| LLM-based structured extraction | Phase 2 of the broader vision -- separate project |
| Geo-database/spatial visualization | Phase 3 of the broader vision -- separate project |
| District-level entity extraction from article content | Phase 2 -- requires LLM |
| Real-time alerting | This is a daily batch pipeline |
| Paid API subscriptions | Zero budget constraint |
| Mobile app or web dashboard | Output is files committed to repo |
| MCP servers at runtime | Batch pipeline, not interactive AI session |
| Selenium/Playwright browser automation | Too heavy; trafilatura handles 90%+ of sites |
| Newspaper homepage scraping | Unreliable; use APIs instead |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 6: Query Engine and Scheduling | Pending |
| COLL-02 | Phase 6: Query Engine and Scheduling | Pending |
| COLL-03 | Phase 6: Query Engine and Scheduling | Pending |
| COLL-04 | Phase 4: Google News RSS Source | Pending |
| COLL-05 | Phase 5: Secondary News Sources | Pending |
| COLL-06 | Phase 5: Secondary News Sources | Pending |
| COLL-07 | Phase 4: Google News RSS Source | Pending |
| COLL-08 | Phase 6: Query Engine and Scheduling | Pending |
| LANG-01 | Phase 3: Heat Terms Dictionary | Pending |
| LANG-02 | Phase 3: Heat Terms Dictionary | Pending |
| LANG-03 | Phase 3: Heat Terms Dictionary | Pending |
| LANG-04 | Phase 3: Heat Terms Dictionary | Pending |
| LANG-05 | Phase 3: Heat Terms Dictionary | Pending |
| EXTR-01 | Phase 7: Article Extraction | Pending |
| EXTR-02 | Phase 7: Article Extraction | Pending |
| EXTR-03 | Phase 7: Article Extraction | Pending |
| DEDU-01 | Phase 8: Deduplication and Filtering | Pending |
| DEDU-02 | Phase 8: Deduplication and Filtering | Pending |
| DEDU-03 | Phase 8: Deduplication and Filtering | Pending |
| FILT-01 | Phase 8: Deduplication and Filtering | Pending |
| FILT-02 | Phase 8: Deduplication and Filtering | Pending |
| FILT-03 | Phase 8: Deduplication and Filtering | Pending |
| FILT-04 | Phase 8: Deduplication and Filtering | Pending |
| DATA-01 | Phase 2: Data Models and Geographic Data | Complete |
| DATA-02 | Phase 2: Data Models and Geographic Data | Complete |
| DATA-03 | Phase 2: Data Models and Geographic Data | Complete |
| OUTP-01 | Phase 9: Output and Reliability | Pending |
| OUTP-02 | Phase 9: Output and Reliability | Pending |
| OUTP-03 | Phase 9: Output and Reliability | Pending |
| OUTP-04 | Phase 9: Output and Reliability | Pending |
| RELI-01 | Phase 9: Output and Reliability | Pending |
| RELI-02 | Phase 9: Output and Reliability | Pending |
| RELI-03 | Phase 9: Output and Reliability | Pending |
| RELI-04 | Phase 9: Output and Reliability | Pending |
| RELI-05 | Phase 9: Output and Reliability | Pending |
| AUTO-01 | Phase 10: Automation | Pending |
| AUTO-02 | Phase 10: Automation | Pending |
| AUTO-03 | Phase 10: Automation | Pending |
| AUTO-04 | Phase 10: Automation | Pending |
| AUTO-05 | Phase 6: Query Engine and Scheduling | Pending |
| INFR-01 | Phase 1: Project Foundation | Complete |
| INFR-02 | Phase 1: Project Foundation | Complete |
| INFR-03 | Phase 1: Project Foundation | Complete |
| INFR-04 | Phase 1: Project Foundation | Complete |
| INFR-05 | Phase 2: Data Models and Geographic Data | Complete |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-02-10*
*Last updated: 2026-02-10 after roadmap creation*
