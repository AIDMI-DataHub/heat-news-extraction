# Heat Season News Extraction Pipeline

## What This Is

A daily automated pipeline that collects heat-related news articles from across all Indian states, union territories, and districts (~800+ entities) in 14+ local languages. It builds a comprehensive database of heatwave impacts — deaths, water scarcity, power outages, crop damage, and human suffering from extreme heat — as the foundation for AIDMI's disaster research, structured extraction, and spatial analysis.

## Core Value

Capture every heat-related news report from every corner of India, in every language, every day — high recall over high precision. Missing real coverage is worse than collecting noise.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Collect heat-related news from all 36 states/UTs and ~770 districts daily
- [ ] Support 14+ Indian languages (en, hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, ur, ne)
- [ ] Comprehensive heat terms dictionary verified against actual regional journalism
- [ ] Deduplicate articles across overlapping state/district queries
- [ ] Output both JSON and CSV formats
- [ ] Run automated daily via GitHub Actions
- [ ] Operate entirely on free tier (zero API budget)
- [ ] Handle crash recovery — resume from where it stopped
- [ ] Extract article full text, not just headlines/URLs
- [ ] Filter for genuine heat/disaster relevance (not weather forecasts or cricket heat maps)

### Out of Scope

- LLM-based structured extraction from article text — Phase 2 of the larger vision
- Geo-database creation and spatial visualization — Phase 3
- District-level entity extraction from article content — Phase 2
- Real-time alerting — this is a daily batch pipeline
- Paid API subscriptions — zero budget constraint
- Mobile app or web dashboard — output is files/database

## Context

**AIDMI (All India Disaster Mitigation Institute)** uses news extraction to track disaster impacts across India. An existing monsoon-news-extraction pipeline at `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/` handles monsoon/flood coverage using a similar approach. That pipeline has known issues with scraping reliability, Google News rate limiting, and crash recovery that this project should learn from but not blindly replicate.

**The broader vision** is a 3-phase system:
1. **Collection** (this project) — Gather all heat-related news into a database
2. **Extraction** — Feed database into LLM to extract structured information (vulnerabilities, locations, impacts, government response, adaptation gaps)
3. **Visualization** — Spatial databases, maps, reports

**Heat season** in India peaks March-June. The pipeline needs to be operational ASAP.

**Scale challenge**: ~800+ entities (36 states/UTs + ~770 districts) queried daily across 14+ languages on free tier. Smart query strategies (batching, hierarchical querying, overlap-aware dedup) are essential.

**Research-first approach**: The user explicitly wants a thorough landscape analysis of modern tools (MCP servers, news APIs, scraping libraries) before any code is written. The monsoon pipeline's approach should be studied but not assumed correct.

## Constraints

- **Budget**: Zero — all APIs and tools must work within free tiers
- **Infrastructure**: GitHub Actions with 45-minute timeout for daily runs
- **Timeline**: Heat season is approaching — need working v1 ASAP
- **Languages**: Must handle 14+ Indian languages with script-native queries (not just English translations)
- **Scale**: ~800+ geographic entities per daily run
- **Output**: Both JSON and CSV files required
- **Approach**: Research and architecture proposal required before any implementation

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Research before build | Monsoon pipeline has known issues; modern tooling landscape has changed significantly | -- Pending |
| State + district level queries | Comprehensive coverage needed; dedup handles overlap | -- Pending |
| Free tier only | Budget constraint; must design around rate limits | -- Pending |
| High recall over precision | Missing real coverage is worse than noise; filtering can happen downstream | -- Pending |
| Focus on Phase 1 (collection) only | Clear scope boundary; Phase 2 (LLM extraction) is separate | -- Pending |

---
*Last updated: 2026-02-10 after initialization*
