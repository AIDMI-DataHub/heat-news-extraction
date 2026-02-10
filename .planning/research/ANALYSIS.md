# Monsoon Pipeline Deep Analysis

**Analyzed:** 2026-02-10
**Repository:** `/Users/akashyadav/Desktop/AIDMI/Github/monsoon-news-extraction/`
**Files reviewed:** All 12 Python/config files, GitHub Actions workflow, CSV database

---

## What Actually Works Well

### 1. Multilingual Architecture (language_map.py)
The `get_all_languages_for_region()` function is well-designed. It maps each state/UT to multiple languages (e.g., Karnataka → `[kn, en, te, ta]`), correctly reflecting India's linguistic reality. The `get_climate_impact_terms()` function provides native-script terms for 16 languages including Meitei and Mizo — a level of coverage most projects skip. **This is worth keeping and extending.**

### 2. URL Date Extraction (monsoon.py:862-909)
The `extract_date_from_url()` function handles 9 different URL date patterns common in Indian news sites (`/2024/3/15/`, `article20240303`, `15_03_2024`, etc.). This is hard-won knowledge about how Indian newspapers structure URLs. **Directly reusable.**

### 3. Content Relevance Filtering Logic (monsoon.py:448-492)
The `is_monsoon_content_relevant()` function checks for term presence in local language, then uses context indicators. The idea of requiring monsoon terms + context clues is sound — it avoids both false positives (cricket articles mentioning "rain") and false negatives (local language articles). The irrelevant pattern exclusion list is practical.

### 4. Smart Google News Handler Pattern (smart_google_news_handler.py)
The circuit breaker pattern, adaptive delay calculation, and per-region rate tracking are well-engineered. The concepts are solid: exponential backoff, time-of-day adjustments, query pattern banning. **The patterns are worth keeping even if the underlying transport (pygooglenews) needs replacement.**

### 5. Newspaper Database (list_of_newspaper_statewise.csv)
Having a curated CSV of Indian newspapers by state, language, and website is valuable domain knowledge. This can feed into RSS discovery, direct scraping targets, and source verification.

### 6. Three-Strategy Article Extraction (article_scraper.py:685-828)
The cascade of requests+newspaper3k → Playwright → Selenium is the right approach. The fallback strategy with trafilatura as an intermediate option is sound. The problem isn't the strategy — it's the execution weight of Selenium.

### 7. Multi-Layer Deduplication (extract_articles.py:480-596)
Three deduplication strategies (URL normalization → content fingerprinting → domain+title matching) is thorough. The quality-aware dedup (keep higher quality version) is smart.

---

## What Is Fundamentally Broken

### 1. pygooglenews Is Effectively Dead
`pygooglenews==0.1.2` is pinned in `actual_requirements.txt`. The library wraps Google News RSS feeds using `feedparser`. **Critical issues:**
- Last meaningful commit was years ago
- Google frequently changes their RSS feed format, breaking the parser
- The `smart_google_news_handler.py` (464 lines) exists entirely because pygooglenews is unreliable — that's a massive red flag
- The circuit breaker pattern means the pipeline regularly fails and just... gives up on regions
- When it works, Google News rate-limits aggressively, especially for automated queries from cloud IPs (GitHub Actions)

**Verdict:** The entire rate limiting, circuit breaker, session rotation infrastructure exists to work around a broken dependency. This is a house of cards.

### 2. Selenium Is a Reliability Nightmare (article_scraper.py)
The `article_scraper.py` file is **1053 lines** — the largest file in the repo — and most of that code is defensive programming against Chrome:
- `DriverWatchdog` thread (lines 136-161) to force-kill hung Chrome processes
- `kill_process_tree()` using psutil to hunt orphaned processes (lines 334-363)
- `safely_quit_driver()` with multiple fallback kill strategies (lines 365-393)
- `TimeoutHandler` using SIGALRM signals (lines 163-177)
- Chrome driver initialization with 6 fallback strategies (lines 179-308)

The GitHub Actions workflow installs Chrome, Xvfb (virtual display), and Playwright browsers — **~500MB+ of dependencies** for what is fundamentally "download HTML and extract text."

**Verdict:** Selenium should be eliminated entirely for a daily batch pipeline. newspaper3k + trafilatura + httpx can handle 95%+ of Indian news sites without a browser.

### 3. No Crash Recovery
If the pipeline crashes at state #15 of 36:
- `cleanup_existing_files_for_date_range()` (monsoon.py:911-990) **deletes existing CSVs before processing** — so partial results from a previous run may be destroyed
- No checkpoint file, no state tracking, no resume capability
- The `EXTRACTION_TIMEOUT` flag in extract_articles.py saves partial results, but only for the extraction phase, not collection
- The GitHub Actions workflow has no retry logic — if it fails, the day's data is simply lost

### 4. Sequential Processing of 36 Regions
`monsoon.py` processes regions in a single for-loop (line 102): one region at a time, one language at a time, one query at a time. With ~5 queries per language × ~2.5 languages per region × 36 regions × adaptive delays = **this easily exceeds 90 minutes.**

The GitHub Actions timeout is 90 minutes (line 29 of the workflow). The pipeline routinely won't finish.

### 5. Data Structure Is Raw Lists
Articles are stored as lists: `[title, link, ist_date_str, source, summary, term, lang_code]` (monsoon.py:441). No dataclass, no Pydantic model, no named tuple. Position-based indexing throughout the code (`entry[2]` for date, `entry[0]` for title). This makes bugs silent and refactoring dangerous.

### 6. Date Parsing Silently Fails
`convert_gmt_to_ist()` (monsoon.py:1048-1058) catches ValueError and returns the raw input string. Downstream code tries to parse this with `datetime.strptime(entry[2].split()[0], "%Y-%m-%d")` (line 163) — if the GMT conversion failed, this also fails silently or crashes. There's no validation chain.

### 7. Folder Creation Is Wasteful (utils.py)
`create_folders()` creates a folder for every day of the year for every state/UT for the Monsoon event type. That's `(28 states + 8 UTs + 1 national) × 365 days = 13,505 empty directories` created upfront. Most will never contain data. Use `os.makedirs(exist_ok=True)` at write time instead.

### 8. Two Requirements Files
`requirements.txt` and `actual_requirements.txt` have **different versions** of the same packages (e.g., `requests==2.31.0` vs `requests==2.28.1`, `selenium==4.15.0` vs `4.10.0`). The GitHub Actions workflow installs packages individually with yet different versions. Nobody knows which versions actually run.

### 9. Google News URL Deduplication Problem
Google News wraps article URLs in redirect URLs like `news.google.com/rss/articles/CBMi...`. The `normalize_url()` function (extract_articles.py:37-76) tries to handle this by extracting the article ID, but:
- The base64 decoding in `decode_google_news_url()` is fragile (bare `except:` clauses)
- Different Google News entries can point to the same article but with different encoded IDs
- The URL normalization removes tracking params but can't resolve the fundamental redirect problem

### 10. Zero Tests
Not a single test file exists. The `verify_dedup.py` is a manual analysis script, not an automated test. Consequences:
- No way to verify relevance filtering isn't too aggressive
- No regression detection when changing query strategies
- No validation of date parsing across formats
- No way to benchmark extraction success rates

---

## What Should Be Questioned Entirely

### Is Google News the Right Primary Data Source?
**Probably not, for this use case.** Problems:
1. Rate limiting makes automated daily extraction unreliable
2. Google News RSS is not an official API — it can change without notice
3. Coverage of regional Indian language news is inconsistent
4. ~800+ queries daily from a GitHub Actions IP will almost certainly get blocked

**Alternatives to investigate:** NewsData.io API (claims 87K+ sources, Indian language support, purpose-built for this), GNews API, direct RSS from Indian newspapers, or a combination.

### Is the Two-Phase Approach Right?
The pipeline collects URLs to CSVs (monsoon.py), then extracts article content from those CSVs (extract_articles.py). This separation made sense when Selenium was needed for extraction. But if we use trafilatura/httpx for extraction:
- Collection and extraction can happen in one pass
- No intermediate CSV files needed
- Deduplication can happen before extraction (saving HTTP requests)
- Failed extractions can be retried immediately

### Is Selenium/Playwright Needed at All?
For a **batch pipeline** extracting news articles, almost certainly not. Modern article extraction libraries (trafilatura, newspaper3k/4k) handle most news sites. The few that require JavaScript rendering could be handled by a lightweight approach (httpx + selectolax) or simply skipped — high recall doesn't require 100% extraction rate.

### Should This Be Async/Parallel?
**Yes.** The sequential approach is the primary bottleneck:
- HTTP requests are I/O bound — perfect for async
- Independent state queries can run in parallel
- httpx supports async natively
- Could process all 36 states simultaneously with proper rate limiting
- Python asyncio + httpx could reduce runtime from 90+ minutes to under 15 minutes

---

## Specific Code Worth Reusing

| Component | Location | Why |
|-----------|----------|-----|
| State/UT lists | language_map.py:51-91 | Complete, correct mapping |
| Language mappings per region | language_map.py:7-43 | Hard-won domain knowledge |
| URL date extraction patterns | monsoon.py:862-909 | Indian news URL formats |
| Newspaper CSV database | list_of_newspaper_statewise.csv | Curated source list |
| Content relevance filter logic | monsoon.py:448-492 | Good approach, needs heat terms |
| Script-based language detection | article_scraper.py:395-432 | Works well for Indian scripts |
| URL normalization patterns | extract_articles.py:37-76 | Tracking param removal |
| Article date extraction strategies | monsoon.py:711-768 | Meta tags, CSS classes, patterns |

## Specific Code to Throw Away

| Component | Why |
|-----------|-----|
| Selenium driver management (article_scraper.py) | 500+ lines of Chrome babysitting |
| SmartGoogleNewsHandler (smart_google_news_handler.py) | Band-aid for a broken dependency |
| Folder pre-creation (utils.py) | Create on write instead |
| main.py subprocess orchestration | subprocess.run for Python scripts is unnecessary |
| process_newspaper_sources (monsoon.py:494-550) | HTML scraping of newspaper homepages is unreliable |

---

## Summary Assessment

The monsoon pipeline is a functional but fragile system. Its core domain knowledge (Indian state/language mappings, news URL patterns, relevance filtering) is valuable. Its infrastructure (Selenium, pygooglenews, sequential processing, no error recovery) is the wrong foundation for a system that needs to reliably process 800+ entities daily on free tier.

**The heat pipeline should reuse the domain knowledge but completely rebuild the infrastructure layer.**

---
*Analysis completed: 2026-02-10*
