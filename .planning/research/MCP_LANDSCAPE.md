# MCP Server & Tooling Landscape Analysis for Heat News Extraction Pipeline

**Date**: 2026-02-10
**Author**: Research agent (Claude Opus 4.6)
**Scope**: Evaluate MCP servers, news APIs, scraping libraries, and RSS tools for daily heat-news extraction across 800+ Indian geographic entities in 14+ languages on zero budget.

**Caveat**: WebSearch and WebFetch tools were unavailable during this research session. Analysis is based on training data through May 2025. Items marked with [VERIFY] should be checked against current GitHub repos and API docs before final architecture decisions. The MCP ecosystem moves fast — repos appear and disappear monthly.

---

## Table of Contents

1. [Scale Analysis: What We Actually Need](#1-scale-analysis)
2. [News API MCP Servers](#2-news-api-mcp-servers)
3. [Web Scraping / Content Extraction MCP Servers](#3-web-scraping-mcp-servers)
4. [RSS Feed MCP Servers](#4-rss-feed-mcp-servers)
5. [Direct APIs and Libraries (No MCP)](#5-direct-apis-and-libraries)
6. [Architecture Decision: MCP vs Direct](#6-architecture-decision)
7. [Free Tier Math: Covering 800+ Entities Daily](#7-free-tier-math)
8. [Recommended Architecture](#8-recommended-architecture)
9. [Risk Register](#9-risk-register)

---

## 1. Scale Analysis: What We Actually Need {#1-scale-analysis}

Before evaluating tools, let's be precise about the volume:

### Naive calculation (worst case)
- 36 states/UTs + ~770 districts = ~806 entities
- 14 languages per entity = 11,284 query combinations
- Daily = **11,284 API calls/day minimum** (one query per entity-language pair)

### Smart calculation (realistic with batching)
- **State-level queries**: 36 states x 14 languages = 504 queries/day
- **District-level queries**: Only for states where heat is active (roughly 15-20 states during peak season) x avg 30 districts = ~500 districts x 3 key languages each = ~1,500 queries/day
- **Total realistic**: ~2,000 queries/day during peak season
- **With query batching** (combining 3-5 districts per query string): ~400-600 effective API calls/day

### What each "query" involves
1. **Search query** to find articles (API call or RSS fetch)
2. **Article fetch** to get full text (HTTP request per article, say 5-20 articles per query)
3. **Total HTTP requests**: ~400 search queries + ~4,000 article fetches = ~4,400 requests/day

This is the number we need to fit within free tiers.

---

## 2. News API MCP Servers {#2-news-api-mcp-servers}

### 2.1 news-mcp (guangxiangdebizi)

**What it claims**: Aggregates 5 news APIs (likely NewsAPI.org, GNews, NewsData.io, Currents API, and possibly TheNewsAPI) with automatic failover.

**Assessment**:
- **Indian language support**: Depends on underlying APIs. NewsAPI.org has limited Indian language support. GNews and NewsData.io are better.
- **Free tier**: Bottlenecked by the weakest link in whatever APIs it wraps. Each underlying API has its own key and limits.
- **For our use case**: The failover concept is good, but MCP wrapping adds overhead for a batch pipeline. We need the same failover logic but in a Python function, not an MCP tool call.
- **Maintenance**: [VERIFY] Likely a small project with <50 stars. MCP server repos with broad scope tend to be thinly maintained.
- **Verdict**: **Skip the MCP wrapper. Steal the failover pattern and implement it in Python.**

### 2.2 Google News & Trends MCP (jmanek)

**What it claims**: Wraps Google News RSS feeds and Google Trends data into MCP tools.

**Assessment**:
- **Indian language support**: Google News RSS supports `hl=hi` (Hindi), `hl=ta` (Tamil), `hl=te` (Telugu), `hl=bn` (Bengali), `hl=mr` (Marathi), `hl=ml` (Malayalam), `hl=kn` (Kannada), and `gl=IN` for India geo. This is excellent — covers most of our 14 languages.
- **Free tier**: Google News RSS is free with no API key. But it rate-limits aggressively — in practice, you get throttled after ~100-200 requests in quick succession from one IP.
- **Google Trends integration**: Useful for identifying which heat terms are actually trending, but secondary to our core need.
- **For our use case**: The RSS parsing is trivial — `feedparser` does it in 3 lines of Python. The MCP wrapper adds zero value for batch use.
- **Maintenance**: [VERIFY] Likely maintained as a demo project.
- **Verdict**: **Skip. Use Google News RSS directly via feedparser + httpx.**

### 2.3 NewsData.io MCP (algonacci)

**What it claims**: MCP server wrapping the NewsData.io API.

**Assessment**:
- **Indian language support**: NewsData.io is the best option here. Claims support for Hindi (hi), Tamil (ta), Telugu (te), Bengali (bn), Marathi (mr), and more. Has `country=in` filter.
- **Free tier**: 200 credits/day on free plan. Each API call = 1 credit. With pagination, a single search returns up to 10 results. So: **200 searches/day returning up to 2,000 article references.**
- **For our use case**: 200 calls/day is tight but usable if we batch smartly (state-level only, not district-level, through this API).
- **Maintenance**: algonacci appears to maintain several MCP wrappers. Quality varies.
- **Verdict**: **Use NewsData.io API directly. The MCP wrapper just adds a JSON-RPC layer we don't need in a cron job.**

### 2.4 GNews MCP (algonacci)

**What it claims**: MCP wrapper for the GNews API.

**Assessment**:
- **Indian language support**: GNews supports `lang=hi`, `lang=ta`, `lang=te`, `lang=bn`, `lang=mr` and `country=in`.
- **Free tier**: 100 requests/day. Each request returns up to 10 articles. So: **100 searches/day, ~1,000 article references.**
- **For our use case**: 100 calls/day is very tight. Only useful as a secondary/failover source.
- **Maintenance**: Same as above (algonacci).
- **Verdict**: **Use GNews API directly as a secondary source. 100/day is not enough as primary.**

### 2.5 Other News MCP Servers Found in the Ecosystem

- **Currents API MCP**: Free tier is 600 requests/day [VERIFY]. Supports some Indian languages. Worth investigating.
- **TheNewsAPI MCP**: 100 free requests/day. Limited Indian language support.
- **Bing News Search**: Part of Azure Cognitive Services. Free tier exists (1,000 calls/month = ~33/day). Not enough alone.
- **MediaStack MCP**: 100 requests/month on free tier. Useless for our scale.

### Summary Table: News API MCP Servers

| Server | Indian Languages | Free Daily Limit | Enough for 800+ entities? | Use MCP? |
|--------|-----------------|-------------------|---------------------------|----------|
| news-mcp (multi-API) | Varies | Varies | Maybe (with all APIs combined) | No — use pattern, not wrapper |
| Google News MCP | 8+ Indian langs | ~200 before throttle | No alone | No — use feedparser |
| NewsData.io MCP | 5+ Indian langs | 200 calls | Partial (state-level) | No — use API directly |
| GNews MCP | 5+ Indian langs | 100 calls | No alone | No — use API directly |

---

## 3. Web Scraping / Content Extraction MCP Servers {#3-web-scraping-mcp-servers}

These are relevant for **Phase 2 of each query** — after finding article URLs, extracting the full text.

### 3.1 Crawl4AI MCP (multiple implementations)

**What it claims**: Open-source, LLM-friendly web crawler. Multiple MCP server implementations exist wrapping the Crawl4AI Python library.

**Assessment**:
- **Indian news sites**: Crawl4AI uses browser automation (Playwright under the hood) or HTTP-based fetching. Works on Indian sites but is overkill for article extraction.
- **GitHub Actions**: Heavy — requires Playwright browser installation (~400MB). Eats into the 45-minute GitHub Actions limit.
- **For our use case**: The **Python library** (crawl4ai) is interesting for difficult-to-scrape sites. But for standard news articles, trafilatura is faster and lighter.
- **MCP overhead**: Significant. Running an MCP server just to call Crawl4AI's Python API makes no sense in a batch pipeline.
- **Verdict**: **Skip MCP. Consider the Python library as a fallback for sites that resist trafilatura.**

### 3.2 Firecrawl MCP (official)

**What it claims**: Commercial scraping service with LLM-ready output. Official MCP server from Firecrawl team.

**Assessment**:
- **Free tier**: 500 credits free (one-time, not monthly) [VERIFY — this changes frequently]. Each page scrape = 1 credit. That's 500 pages total, ever. Completely inadequate.
- **Indian news sites**: Works well — handles JavaScript-rendered sites.
- **GitHub Actions**: Easy — it's an API call. But the free tier dies in one day of our pipeline.
- **Verdict**: **Hard no. Zero-budget constraint kills this option immediately.**

### 3.3 Bright Data Web MCP

**What it claims**: Proxy-based scraping with CAPTCHA bypass, anti-bot evasion, through MCP interface.

**Assessment**:
- **Free tier**: Bright Data offers a free trial but no perpetual free tier. This is an enterprise product.
- **For our use case**: Way overkill and way over budget (which is zero).
- **Verdict**: **Hard no. Not free.**

### 3.4 Playwright MCP (official Anthropic)

**What it claims**: Browser automation through MCP tools. Can navigate, click, fill forms, screenshot, extract text.

**Assessment**:
- **For our use case**: This is designed for interactive browser automation in Claude Code sessions. For a batch pipeline, you'd use Playwright's Python library directly, not through MCP.
- **Indian news sites**: Playwright handles everything — JavaScript rendering, Indian language fonts, dynamic loading. But it's slow (~3-5 seconds per page vs <1 second for HTTP+trafilatura).
- **GitHub Actions**: Works but heavy. `playwright install chromium` adds significant setup time.
- **Verdict**: **Skip MCP entirely. If we need browser rendering, use playwright Python library directly as last resort.**

### Summary: Scraping MCP Servers

**None of these MCP servers are appropriate for our batch pipeline.** For article text extraction, use Python libraries directly:

| Need | Tool | Why |
|------|------|-----|
| Article text extraction (90% of sites) | trafilatura | Fast, no browser, handles Indian languages |
| JavaScript-rendered sites (10%) | crawl4ai or playwright (Python) | Fallback only |
| Anti-bot bypass | Not needed | Indian regional news sites have minimal bot protection |

---

## 4. RSS Feed MCP Servers {#4-rss-feed-mcp-servers}

### 4.1 rss-mcp (veithly)

**What it claims**: RSS/Atom feed parser with RSSHub failover. Parses feeds and returns structured data.

**Assessment**:
- **RSSHub Indian routes**: This is the critical question. RSSHub (rsshub.app) has routes for some Indian sources: NDTV, The Hindu, Times of India, Indian Express, Hindustan Times. But coverage of **regional language newspapers** is very sparse. You won't find routes for Dainik Jagran (Hindi), Anandabazar Patrika (Bengali), Dinamalar (Tamil), or Eenadu (Telugu) — which are exactly the sources we need for multi-language coverage.
- **Reliability**: RSS feeds are more reliable than scraping but less comprehensive than API searches. You get what the feed provides — typically the last 20-50 articles.
- **MCP value**: Zero for batch pipeline. feedparser + httpx does the same thing.
- **Verdict**: **Skip MCP. RSS feeds are useful as ONE data source, but not comprehensive enough alone. Use feedparser directly.**

### 4.2 feed-mcp (richardwooding)

**What it claims**: RSS/Atom/JSON feed reader as MCP tools.

**Assessment**: Same conclusion as rss-mcp. The MCP wrapper adds nothing for batch use. `feedparser` is 10 lines of code.

### 4.3 RSS MCP (missionsquad)

**What it claims**: Enterprise RSS with caching and scheduling.

**Assessment**: The caching is interesting but we'd implement our own caching in the pipeline anyway. Skip.

### 4.4 RSS Feed Manager (Buhe)

**What it claims**: SQLite-backed RSS management with Firecrawl integration for full-text extraction.

**Assessment**: Firecrawl dependency = not free. The SQLite feed tracking concept is good but trivial to implement.

### Summary: RSS MCP Servers

**None worth using as MCP.** RSS feeds themselves ARE valuable as a data source — Google News RSS is essentially an RSS feed. But the MCP wrappers add nothing for a batch pipeline.

**Key finding on RSSHub**: [VERIFY] Check https://docs.rsshub.app for current Indian news routes. As of mid-2025, coverage of Indian regional language newspapers was poor. If someone has added routes for major Hindi/Tamil/Telugu papers since then, RSSHub becomes much more valuable. Otherwise, we're better off maintaining our own list of RSS feed URLs for Indian news sources.

---

## 5. Direct APIs and Libraries (No MCP) {#5-direct-apis-and-libraries}

This is where the real solution lives.

### 5.1 NewsData.io API (Direct)

- **Sources**: Claims 87,000+ from 150+ countries. India is well-represented.
- **Indian languages**: hi, ta, te, bn, mr confirmed. Possibly gu, kn, ml, pa — [VERIFY current language list].
- **Free tier**: 200 credits/day (was 30/day until they expanded it; [VERIFY] this may have changed again by Feb 2026).
- **Key features**: `q` parameter for keyword search, `country=in`, `language=hi`, `category=environment` or `category=top`, `timeframe=24` for last 24 hours.
- **Rate limit**: 1 request/second on free tier.
- **Reliability**: API is stable. Has been running for years. Good uptime.
- **Maintenance**: Commercial product, actively maintained.
- **For 800+ entities**: 200 calls/day covers state-level queries (36 states x 5-6 key languages = ~200). Not enough for district-level.
- **Verdict**: **PRIMARY source for state-level queries. Use all 200 daily credits strategically.**

### 5.2 GNews API (Direct)

- **Sources**: 60,000+ from 40+ countries.
- **Indian languages**: hi, ta, te, bn, mr, ml, kn — good coverage.
- **Free tier**: 100 requests/day. Each returns up to 10 articles. 1 request/second.
- **Reliability**: Stable commercial API.
- **For 800+ entities**: 100 calls = supplementary source. Use for high-priority states/languages that NewsData.io doesn't cover well.
- **Verdict**: **SECONDARY source. 100 calls/day as failover/supplement.**

### 5.3 Google News RSS (Direct via feedparser)

- **Sources**: Everything Google indexes. The most comprehensive source.
- **Indian languages**: Supports hl=hi, hl=ta, hl=te, hl=bn, hl=mr, hl=ml, hl=kn, hl=gu via URL parameters.
- **Free tier**: No API key. No official rate limit. But Google throttles aggressively — expect 429 errors after ~100-200 rapid requests from one IP.
- **pygooglenews**: Python wrapper library. [VERIFY maintenance status — it was semi-maintained as of 2025. The underlying approach (scraping Google News search results via RSS URLs) still works but the library may not handle all edge cases.]
- **Key approach**: Construct URLs like `https://news.google.com/rss/search?q=heatwave+Delhi&hl=hi&gl=IN&ceid=IN:hi` and parse with feedparser.
- **Rate limit mitigation**: Add 2-3 second delays between requests. Use rotating user agents. Spread queries across the 45-minute GitHub Actions window.
- **Realistic daily capacity**: With 2-second delays, ~1,200 requests in 40 minutes. With error handling and retries, realistically **600-800 queries/day**.
- **Verdict**: **WORKHORSE source. Free, comprehensive, good Indian language support. Must be rate-limit-aware. Don't use pygooglenews — build our own thin wrapper around feedparser + httpx for better control.**

### 5.4 RSSHub (Self-hosted or public instances)

- **What it is**: Open-source RSS feed generator. Converts websites without RSS into RSS feeds.
- **Indian news routes**: [VERIFY] As of mid-2025: NDTV, The Hindu, Times of India, Indian Express have routes. Regional language papers mostly absent.
- **Self-hosting**: Possible on GitHub Actions? No — it's a Node.js server. Could deploy to free tier of Vercel/Railway, but that's infrastructure to maintain.
- **Public instances**: rsshub.app is available but frequently overloaded.
- **Verdict**: **Not viable as primary source. Too few Indian regional routes. Useful if specific routes exist for papers we need.**

### 5.5 Trafilatura (Article Extraction)

- **What it is**: Python library for extracting article text, metadata, and content from web pages. No browser needed.
- **Indian language support**: Excellent. It extracts text regardless of language/script. Handles Devanagari, Tamil, Telugu, Bengali scripts fine.
- **Speed**: ~0.1-0.3 seconds per article (vs 3-5s for Playwright).
- **Reliability**: Handles 85-90% of news sites well. Fails on heavily JavaScript-dependent sites.
- **Maintenance**: Actively maintained by adbar (Adrien Barbaresi). Regular releases. Solid project.
- **For our use case**: This is the **primary article extraction tool**. After getting URLs from news APIs, trafilatura fetches and extracts the article text.
- **Verdict**: **MUST USE. Primary article text extraction. No alternative comes close for this use case.**

### 5.6 Crawl4AI Python Library

- **What it is**: Async web crawler designed for LLM data extraction. Uses Playwright under the hood.
- **Indian news sites**: Works well but heavyweight.
- **Speed**: 3-5 seconds per page (browser rendering).
- **GitHub Actions**: Requires Playwright browser installation. Adds ~2 minutes setup + significant runtime.
- **Maintenance**: [VERIFY] Active development as of 2025, growing community.
- **Verdict**: **Fallback only. Use when trafilatura fails on a specific site. Don't use as primary.**

### 5.7 newspaper3k / newspaper4k

- **newspaper3k**: Essentially abandoned. Last meaningful commit was years ago. Known issues with Python 3.10+.
- **newspaper4k**: Community fork. [VERIFY] More actively maintained but still has issues.
- **Indian language support**: Basic. NLP features (summary, keywords) don't work well for non-English.
- **vs trafilatura**: trafilatura is faster, more reliable, better maintained, and handles Indian sites better.
- **Verdict**: **Skip. trafilatura is strictly better for our use case.**

### 5.8 httpx

- **What it is**: Modern async HTTP client for Python. Successor to requests for async workflows.
- **Key features**: Async support, HTTP/2, proper timeout handling, connection pooling.
- **For our use case**: Essential infrastructure. Use httpx as the HTTP client for all API calls and direct page fetches.
- **Verdict**: **MUST USE. Core HTTP infrastructure. Use async mode for parallel fetching.**

### 5.9 Mozilla Readability (via readability-lxml or similar)

- **What it is**: Algorithm for extracting article content from web pages. Originally from Firefox Reader Mode.
- **Python ports**: readability-lxml, python-readability.
- **vs trafilatura**: trafilatura includes Readability-like extraction plus additional heuristics. trafilatura is the superset.
- **Verdict**: **Skip. trafilatura already incorporates this approach.**

---

## 6. Architecture Decision: MCP vs Direct {#6-architecture-decision}

### The clear answer: DO NOT use MCP servers for the batch pipeline.

**Why MCP is wrong for this pipeline:**

1. **MCP is a protocol for interactive AI tool use.** It's designed for Claude Code, Cursor, Windsurf, and similar AI coding assistants to call tools during a conversation. Our pipeline is a daily cron job.

2. **MCP adds infrastructure overhead.** Each MCP server is a separate process (stdio or HTTP). For a GitHub Actions workflow, you'd need to start MCP servers, connect to them, make calls through JSON-RPC, and shut them down. This adds startup time, complexity, and failure modes — all for tools that are trivially called as Python functions.

3. **MCP provides no batching optimization.** MCP tools are designed for single interactive calls. Our pipeline needs to make 600+ API calls with rate limiting, retry logic, and parallel execution. Python's asyncio + httpx handles this natively.

4. **MCP wrappers are thin and fragile.** Most news MCP servers are hobby projects with <50 stars. They wrap an API that we can call in 5 lines of Python. When they break (and they will), we're debugging someone else's wrapper instead of our own 5 lines.

5. **Error handling is opaque through MCP.** When a news API returns a rate limit error, we need to catch it, wait, retry with backoff, maybe fail over to a different API. MCP's tool-call abstraction makes this harder, not easier.

### When MCP IS useful for this project:

- **During development**: Use Google News MCP, NewsData.io MCP in Claude Code to interactively explore what queries return, test search terms, verify language support. Then throw away the MCP servers and implement the production version in pure Python.
- **For Phase 2 (LLM extraction)**: If we use Claude to extract structured data from articles, the pipeline itself becomes the "tool provider" and Claude is the consumer. But that's a different architecture discussion.

### Verdict: Pure Python pipeline with direct API calls. Use MCP during development only.

---

## 7. Free Tier Math: Covering 800+ Entities Daily {#7-free-tier-math}

### Available free resources per day

| Source | Daily Free Limit | Articles per Call | Effective Daily Articles |
|--------|-----------------|-------------------|-------------------------|
| Google News RSS | ~600-800 queries (rate-limited) | 10-50 per query | 6,000-20,000 |
| NewsData.io API | 200 credits | 10 per call | 2,000 |
| GNews API | 100 requests | 10 per call | 1,000 |
| Currents API [VERIFY] | ~600 requests | 10 per call | 6,000 |
| **Total search capacity** | **~1,500-1,700 queries/day** | | **~15,000-29,000 article refs** |

### Required queries with smart batching

| Tier | Entities | Languages | Batching | Queries Needed |
|------|----------|-----------|----------|---------------|
| State-level (all) | 36 | 5 key languages | None | 180 |
| State-level (all) | 36 | 14 languages | None | 504 |
| District-level (hot states) | ~300 active | 3 key languages | 5 districts/query | 180 |
| **Total (smart strategy)** | | | | **~700-900** |

### Allocation strategy

1. **Google News RSS** (free, best volume): 500-600 queries = all state-level queries across all 14 languages + district-level batched queries. This is the workhorse.
2. **NewsData.io** (200/day): State-level queries in 5-6 key languages (36 x 5 = 180 queries). Covers gaps where Google News RSS might miss things.
3. **GNews** (100/day): Top 20 most heat-affected states in English + Hindi (40 queries) + 60 for emerging situations.
4. **Reserve**: ~100 Google News RSS capacity for retries and breaking news.

### The math works — barely.

With smart batching and strategic allocation:
- **~900 search queries/day** covers all 36 states in 14 languages + 300 active districts in 3 languages.
- **~1,500-1,700 queries/day capacity** across all free tiers combined.
- **Margin**: ~600-800 queries/day buffer for retries, errors, and additional searches.

### What happens when free tiers run out mid-month?

- **Google News RSS**: Doesn't have a hard monthly cap. It rate-limits per session. Solution: spread requests over the 45-minute window with delays.
- **NewsData.io**: 200/day is daily, not monthly. Resets every 24 hours. Won't "run out mid-month."
- **GNews**: Same — 100/day resets daily.
- **Risk**: If Google News starts returning 429 errors more aggressively, we lose our primary source. **Mitigation**: If Google News degrades, shift more queries to paid NewsData.io plan ($49/month for 6,000 requests/day) — but that violates zero-budget. So the real mitigation is: build the pipeline to gracefully degrade. If Google News is throttled today, we still get data from NewsData.io and GNews. Completeness drops but pipeline doesn't fail.

---

## 8. Recommended Architecture {#8-recommended-architecture}

### Data flow

```
[Query Generator]
    |
    v
[Multi-Source Search Layer]
    |-- Google News RSS (primary, ~600 queries)
    |-- NewsData.io API (secondary, ~200 queries)
    |-- GNews API (tertiary, ~100 queries)
    |
    v
[URL Deduplication]
    |
    v
[Article Extraction] -- trafilatura (primary)
    |                 -- crawl4ai (fallback for JS-heavy sites)
    |
    v
[Storage] -- JSON + CSV output
```

### Core Python stack

```
httpx          -- async HTTP client for all requests
feedparser     -- Google News RSS parsing
trafilatura    -- article text extraction (primary)
aiofiles       -- async file I/O
tenacity       -- retry with exponential backoff
pydantic       -- data validation/models
```

### Key design principles

1. **Source-agnostic query interface**: Each news source (Google RSS, NewsData.io, GNews) implements the same interface: `search(query, language, country) -> List[ArticleRef]`. The pipeline doesn't care which source returned the result.

2. **Rate-limit-aware scheduler**: Knows each source's limits. Distributes queries across sources. Respects delays. Implements per-source circuit breakers.

3. **Hierarchical querying**: Query states first. For states with results, query their districts. Skip districts in states with no heat news.

4. **Aggressive deduplication**: Same article appears in multiple state/district/language queries. Deduplicate by URL (normalized), then by title similarity for cross-language duplicates.

5. **Crash recovery**: Track which queries succeeded. On restart, skip completed queries. Use a SQLite file or JSON checkpoint.

6. **45-minute budget**: GitHub Actions limit. With 2-second delays between Google News requests, ~1,200 requests fit in 40 minutes. With parallel API calls to NewsData.io and GNews (they have separate rate limits), total throughput is higher.

### What NOT to use

| Tool | Why Not |
|------|---------|
| Any MCP server | Batch pipeline, not interactive AI session |
| Firecrawl | Not free |
| Bright Data | Not free |
| newspaper3k | Abandoned; trafilatura is better |
| Playwright (as primary) | Too slow for 4,000+ article fetches |
| pygooglenews | Semi-maintained; build own thin wrapper |
| Selenium | Playwright is better if browser needed |

---

## 9. Risk Register {#9-risk-register}

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Google News throttling increases | Lose primary source (~60% of queries) | Diversify: increase NewsData.io/GNews allocation. Consider Currents API. Implement IP rotation if possible (hard on GitHub Actions). |
| NewsData.io reduces free tier | Lose 200 queries/day | Google News RSS can absorb this load with slower pacing. |
| Indian regional news sites block scrapers | Can't extract article text | trafilatura handles most sites. For blocks, try adding newspaper-specific User-Agent headers. Last resort: headless browser. |
| 45-minute GitHub Actions timeout | Pipeline doesn't finish | Prioritize: do state-level first (guaranteed to complete in 15 min), then districts. Use checkpoint/resume. Split into multiple workflow runs if needed. |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Indian language queries return poor results | Low recall for non-English | Build comprehensive heat term dictionaries validated against actual journalism in each language. Test terms before hardcoding. |
| Deduplication across languages fails | Inflated article counts, wasted storage | Use URL normalization as primary dedup. Title similarity (Jaccard on character n-grams) as secondary. |
| GitHub Actions IP gets flagged | Increased rate limiting | Implement polite crawling: respect robots.txt, add delays, use realistic User-Agent strings. |

### Low Risk (but worth tracking)

| Risk | Impact | Mitigation |
|------|--------|------------|
| New free news API appears | Opportunity to increase coverage | Monitor MCP server listings and news API aggregators quarterly. |
| GNews API changes free tier | Minor — it's only 100/day | Already a secondary source. |

---

## Appendix A: Verification Checklist

The following items should be verified with live web research before finalizing the architecture:

- [ ] NewsData.io free tier: Is it still 200 credits/day in Feb 2026?
- [ ] NewsData.io Indian language list: Which of our 14 languages are supported?
- [ ] GNews free tier: Still 100 requests/day?
- [ ] Currents API: Free tier limits? Indian language support?
- [ ] pygooglenews: Last commit date and Python 3.11+ compatibility?
- [ ] RSSHub Indian routes: Check https://docs.rsshub.app for Dainik Jagran, Amar Ujala, Dinamalar, Eenadu, Anandabazar Patrika routes.
- [ ] Crawl4AI: Current version and GitHub Actions compatibility?
- [ ] GitHub Actions: Current free tier limits for public repos (minutes/month)?
- [ ] newspaper4k: Maintenance status and comparison with trafilatura?
- [ ] Google News RSS: Current rate limiting behavior from GitHub Actions IPs (cloud IPs may be more aggressively throttled than residential).

## Appendix B: Quick Comparison Matrix

| Criterion | Google News RSS | NewsData.io | GNews | Currents [VERIFY] |
|-----------|----------------|-------------|-------|-------------------|
| Free daily limit | ~600-800 (soft) | 200 (hard) | 100 (hard) | ~600 (hard) |
| API key needed | No | Yes | Yes | Yes |
| Indian languages | 8+ | 5+ | 7+ | Unknown |
| District-level precision | Good (via query) | Good | Good | Unknown |
| Full article text | No (title+link only) | Partial (some content) | Partial | Unknown |
| Reliability | Medium (throttling) | High | High | Medium |
| Best use in pipeline | Primary search | Secondary search | Tertiary search | Backup |

## Appendix C: Why Not Just Use One API?

No single free API covers our needs:

- **Google News RSS alone**: Best volume but aggressive throttling from cloud IPs. If GitHub Actions IP gets flagged, we lose everything.
- **NewsData.io alone**: Only 200/day. Covers state-level but not districts.
- **GNews alone**: Only 100/day. Nowhere near enough.
- **Combined**: ~900-1,100 reliable queries/day. Enough for smart batching strategy. If one source degrades, others cover the gap.

**The architecture MUST be multi-source with failover. No single point of failure.**

---

*End of landscape analysis. Next step: Architecture design document with specific API schemas, query strategies, and GitHub Actions workflow design.*
