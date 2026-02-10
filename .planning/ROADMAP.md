# Roadmap: Heat News Extraction Pipeline

## Overview

This roadmap delivers a daily automated pipeline that collects heat-related news from all Indian states, union territories, and districts in 14+ languages. The journey starts with project scaffolding and data models, builds the multilingual heat terms dictionary, implements three news sources behind a common interface, orchestrates queries at scale with hierarchical batching, extracts full article text, deduplicates and filters for relevance, produces structured JSON/CSV output with crash recovery, and culminates in fully automated daily runs via GitHub Actions. Ten phases, each delivering a coherent, verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Foundation** - Python project scaffolding, dependencies, single entry point ✓ 2026-02-10
- [x] **Phase 2: Data Models and Geographic Data** - Pydantic article models, state/district/language master data ✓ 2026-02-10
- [x] **Phase 3: Heat Terms Dictionary** - 450+ terms across 14 languages, 8 categories per language ✓ 2026-02-10
- [x] **Phase 4: Google News RSS Source** - Primary news source with common search interface ✓ 2026-02-10
- [ ] **Phase 5: Secondary News Sources** - NewsData.io and GNews adapters behind common interface
- [ ] **Phase 6: Query Engine and Scheduling** - Hierarchical querying, smart batching, rate-limit-aware scheduler
- [ ] **Phase 7: Article Extraction** - Full text extraction from collected URLs using trafilatura
- [ ] **Phase 8: Deduplication and Filtering** - URL/title dedup, relevance scoring, high-recall filtering
- [ ] **Phase 9: Output and Reliability** - JSON/CSV output, checkpoint/resume, circuit breakers
- [ ] **Phase 10: Automation** - GitHub Actions workflow, 45-minute constraint, daily commit cycle

## Phase Details

### Phase 1: Project Foundation
**Goal**: A runnable Python project skeleton exists with all dependencies installed and a single entry point that can be invoked
**Depends on**: Nothing (first phase)
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04
**Success Criteria** (what must be TRUE):
  1. Running `python main.py` (or equivalent entry point) executes without import errors and exits cleanly
  2. All core dependencies (httpx, feedparser, trafilatura, pydantic, tenacity, aiofiles) are installed from a pinned requirements.txt
  3. No browser dependencies (Selenium, Playwright) exist anywhere in the dependency tree
  4. Project has a clear directory structure with separate modules for sources, models, extraction, and output
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md -- Project scaffolding, pinned dependencies, and working entry point

### Phase 2: Data Models and Geographic Data
**Goal**: All core data types are defined as Pydantic models and the complete geographic/language master data is available as structured data
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, INFR-05
**Success Criteria** (what must be TRUE):
  1. An Article Pydantic model exists with all required typed fields (title, url, source, date, language, state/district, full_text, search_term, relevance_score) and validates correctly
  2. All dates in the Article model are validated as ISO format with IST timezone -- invalid dates are rejected
  3. A structured data file contains all 36 states/UTs and ~770 districts with their associated languages
  4. The state/district data correctly maps each entity to its relevant languages (e.g., Tamil Nadu maps to Tamil, English)
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md -- Pydantic ArticleRef and Article models with IST date validation
- [ ] 02-02-PLAN.md -- State/district/language master data JSON and Pydantic-validated loader

### Phase 3: Heat Terms Dictionary
**Goal**: A complete, structured multilingual heat terms dictionary is available for query generation across all 14 languages
**Depends on**: Phase 2
**Requirements**: LANG-01, LANG-02, LANG-03, LANG-04, LANG-05
**Success Criteria** (what must be TRUE):
  1. The dictionary contains native-script terms for all 14 languages (en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne)
  2. Each language covers all 8 term categories: heatwave, death/stroke, water crisis, power cuts, crop damage, human impact, government response, temperature
  3. Both formal/official terms (IMD terminology) and colloquial/journalistic terms (e.g., "loo" in Hindi) are included for each language
  4. Borrowed English terms (heat wave, heat stroke, load shedding, red alert) are included in every regional language's term set
  5. Terms are structured data (not free text) that can be programmatically combined with location names for query generation
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md -- JSON schema structure, Pydantic loader, and English/Hindi terms
- [ ] 03-02-PLAN.md -- Remaining 12 language term sets and __init__.py re-exports

### Phase 4: Google News RSS Source
**Goal**: The pipeline can search Google News RSS for heat-related articles and return structured results through a common source interface
**Depends on**: Phase 2
**Requirements**: COLL-04, COLL-07
**Success Criteria** (what must be TRUE):
  1. A GoogleNewsSource class implements the common interface: search(query, language, country) -> List[ArticleRef]
  2. Running a search for a known heat term + state combination returns actual Google News RSS results parsed into ArticleRef objects
  3. The source handles Google News RSS pagination and returns article title, URL, source name, and publication date
  4. The source handles HTTP errors, timeouts, and empty results gracefully without crashing
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md -- NewsSource Protocol and GoogleNewsSource RSS adapter

### Phase 5: Secondary News Sources
**Goal**: NewsData.io and GNews are available as additional search sources behind the same common interface
**Depends on**: Phase 4
**Requirements**: COLL-05, COLL-06
**Success Criteria** (what must be TRUE):
  1. A NewsDataSource class implements the common interface and returns results from NewsData.io API
  2. A GNewsSource class implements the common interface and returns results from GNews API
  3. Each source respects its daily API limit (200/day for NewsData.io, 100/day for GNews) and stops requesting when exhausted
  4. Both sources handle API errors, rate limits, and authentication issues gracefully without crashing
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md -- NewsData.io source adapter with daily quota tracking
- [ ] 05-02-PLAN.md -- GNews source adapter with language filtering and quota tracking

### Phase 6: Query Engine and Scheduling
**Goal**: The pipeline intelligently generates and executes queries across all sources, covering all states/districts with hierarchical batching and rate-limit awareness
**Depends on**: Phase 3, Phase 5
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-08, AUTO-05
**Success Criteria** (what must be TRUE):
  1. The query engine generates heat term + location queries for all 36 states/UTs across relevant languages
  2. District-level queries use smart batching (multiple districts per query) to stay within API limits
  3. Hierarchical querying works: state-level queries execute first, district-level queries follow for states with active results
  4. The rate-limit-aware scheduler distributes queries across Google News RSS, NewsData.io, and GNews based on each source's capacity
  5. Queries execute asynchronously using httpx async, processing multiple sources/states in parallel
**Plans**: TBD

Plans:
- [ ] 06-01: Query generator (terms + locations + languages)
- [ ] 06-02: Rate-limit-aware multi-source scheduler
- [ ] 06-03: Async execution engine with hierarchical querying

### Phase 7: Article Extraction
**Goal**: The pipeline extracts full article text from collected URLs, handling Indian language scripts correctly
**Depends on**: Phase 4
**Requirements**: EXTR-01, EXTR-02, EXTR-03
**Success Criteria** (what must be TRUE):
  1. Given a list of article URLs, trafilatura extracts full article text (not just headlines) for the majority of Indian news sites
  2. Extraction correctly preserves Devanagari, Tamil, Telugu, Bengali, and other Indian scripts without corruption or mojibake
  3. Failed extractions (blocked sites, timeouts, paywalls) are logged with the URL and reason but do not halt the pipeline
  4. Extraction results are stored in the Article model's full_text field
**Plans**: TBD

Plans:
- [ ] 07-01: Trafilatura extraction with Indian script handling

### Phase 8: Deduplication and Filtering
**Goal**: The pipeline removes duplicate articles and filters for genuine heat/disaster relevance while maintaining high recall
**Depends on**: Phase 7
**Requirements**: DEDU-01, DEDU-02, DEDU-03, FILT-01, FILT-02, FILT-03, FILT-04
**Success Criteria** (what must be TRUE):
  1. Articles with the same normalized URL (tracking params removed, redirects resolved) are deduplicated, keeping the higher-quality version
  2. Articles with highly similar titles from different queries/sources are detected as duplicates across languages
  3. Relevance filtering scores articles using term presence + context indicators and excludes clearly irrelevant content (weather forecasts, cricket, generic summer articles)
  4. A configurable irrelevant pattern exclusion list exists and can be updated without code changes
  5. Borderline articles are kept (high recall) -- the filter errs on the side of inclusion, not exclusion
**Plans**: TBD

Plans:
- [ ] 08-01: URL normalization and URL-based deduplication
- [ ] 08-02: Title similarity deduplication
- [ ] 08-03: Relevance scoring and filtering

### Phase 9: Output and Reliability
**Goal**: The pipeline produces organized JSON/CSV output files and can recover from crashes by resuming from checkpoints
**Depends on**: Phase 8
**Requirements**: OUTP-01, OUTP-02, OUTP-03, OUTP-04, RELI-01, RELI-02, RELI-03, RELI-04, RELI-05
**Success Criteria** (what must be TRUE):
  1. Pipeline outputs JSON files organized by date and state/UT, with directories created on write
  2. Pipeline outputs CSV files organized by date and state/UT, matching the JSON structure
  3. Output includes metadata: collection timestamp, sources queried, query terms used, articles found/extracted/filtered counts
  4. After each completed query batch, a checkpoint is saved; restarting the pipeline skips already-completed queries
  5. Each news source has an independent circuit breaker -- if one source fails repeatedly, others continue operating
  6. Rate limit errors trigger exponential backoff with jitter (via tenacity), not immediate failure
**Plans**: TBD

Plans:
- [ ] 09-01: JSON and CSV output writers
- [ ] 09-02: Checkpoint and resume system
- [ ] 09-03: Circuit breakers and retry logic

### Phase 10: Automation
**Goal**: The pipeline runs automatically every day via GitHub Actions, completes within the 45-minute window, and commits results to the repository
**Depends on**: Phase 9
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04
**Success Criteria** (what must be TRUE):
  1. A GitHub Actions workflow triggers the pipeline daily on a cron schedule
  2. The pipeline completes a full run (state-level queries guaranteed, district-level best-effort) within 45 minutes
  3. The workflow operates on zero API budget -- only free-tier sources are used (no paid keys required)
  4. After collection, the workflow commits and pushes the new data files to the repository
  5. If the pipeline is interrupted mid-run, the next day's run starts fresh (or resumes, using the checkpoint system from Phase 9)
**Plans**: TBD

Plans:
- [ ] 10-01: GitHub Actions workflow and environment setup
- [ ] 10-02: Time-budget management for 45-minute constraint

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation | 1/1 | Complete | 2026-02-10 |
| 2. Data Models and Geographic Data | 2/2 | Complete | 2026-02-10 |
| 3. Heat Terms Dictionary | 2/2 | Complete | 2026-02-10 |
| 4. Google News RSS Source | 1/1 | Complete | 2026-02-10 |
| 5. Secondary News Sources | 0/2 | Not started | - |
| 6. Query Engine and Scheduling | 0/3 | Not started | - |
| 7. Article Extraction | 0/1 | Not started | - |
| 8. Deduplication and Filtering | 0/3 | Not started | - |
| 9. Output and Reliability | 0/3 | Not started | - |
| 10. Automation | 0/2 | Not started | - |
