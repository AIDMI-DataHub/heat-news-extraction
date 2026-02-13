# Heat News Extraction Pipeline

Automated daily collection of heat and heatwave news from across India -- covering all 36 states and union territories, ~700 districts, in 14 Indian languages.

Runs as a GitHub Actions workflow every day at 12:00 noon IST. Collects articles from three news sources, filters them with LLM-based relevance checking, extracts full text, tags geographic locations down to the district level, deduplicates, and writes structured JSON/CSV output organized by state, date, and district.

Built for [AIDMI](https://github.com/AIDMI-DataHub) (All India Disaster Mitigation Institute) to support heat-related disaster monitoring and response.

## How It Works

```
 Google News RSS ─┐
 NewsData.io API ─┼─→ Collect ─→ Date Filter ─→ LLM Relevance ─→ Extract ─→ District Tag ─→ Dedup ─→ Output
 GNews API ───────┘    refs        (today)       (title check)     (HTML→text)   (LLM)       (URL+title)  (JSON/CSV)
```

The pipeline is a cost funnel -- cheapest filters run first to minimize expensive operations:

| Stage | What | Input | Output |
|-------|------|-------|--------|
| **1. Collection** | Search queries in 14 languages across all states | Geographic data + heat terms | ~8,000-15,000 article refs |
| **2. Date filter** | Keep only today's articles | All refs | ~500-700 refs |
| **2b. LLM relevance** | GPT-4o-mini checks if title is about heat in the correct state | Titles only | ~40-80 refs |
| **3. Extraction** | Fetch HTML, extract article text via trafilatura | Relevant refs | Articles with full text |
| **3b. District tag (text)** | Match English district names in title + body | Extracted articles | Some articles get districts |
| **3c. District tag (LLM)** | LLM identifies district for remaining articles | Untagged articles | Most articles get districts |
| **4. Dedup** | URL normalization + title similarity (cosine 0.85) + exclusion patterns | All articles | Deduplicated articles |
| **5. Output** | Write per-state, per-district JSON and CSV | Final articles | Structured output files |

## Output Structure

```
output/
  rajasthan/
    2026-04-15/
      articles.json          # State-level articles (multi-district or untagged)
      articles.csv
      jaipur/
        articles.json        # District-level articles
        articles.csv
      jodhpur/
        articles.json
        articles.csv
  delhi/
    2026-04-15/
      articles.json
      articles.csv
      new-delhi/
        articles.json
        articles.csv
  _metadata.json             # Collection metadata (timestamp, sources, counts)
```

### Article JSON format

```json
{
  "state": "Rajasthan",
  "district": "Jaipur",
  "date": "2026-04-15",
  "article_count": 5,
  "articles": [
    {
      "title": "जयपुर में पारा 47 डिग्री के पार, लू से 3 की मौत",
      "url": "https://example.com/article",
      "source": "Dainik Bhaskar",
      "date": "2026-04-15T14:30:00+05:30",
      "language": "hi",
      "state": "Rajasthan",
      "district": "Jaipur",
      "search_term": "(लू OR \"भीषण गर्मी\" OR ...) Rajasthan",
      "full_text": "जयपुर में आज अधिकतम तापमान 47.2 डिग्री ...",
      "relevance_score": 0.85
    }
  ]
}
```

## Languages

Searches are conducted in each state's regional language(s) plus English. 14 languages are supported:

| Language | Script | States |
|----------|--------|--------|
| English | Latin | All 36 states/UTs |
| Hindi | Devanagari | Delhi, UP, MP, Rajasthan, Bihar, Jharkhand, Chhattisgarh, Haryana, HP, Uttarakhand, J&K, Ladakh, Chandigarh, and others |
| Tamil | Tamil | Tamil Nadu, Puducherry |
| Telugu | Telugu | Andhra Pradesh, Telangana |
| Bengali | Bengali | West Bengal, Tripura |
| Marathi | Devanagari | Maharashtra |
| Gujarati | Gujarati | Gujarat, Dadra & Nagar Haveli |
| Kannada | Kannada | Karnataka |
| Malayalam | Malayalam | Kerala, Lakshadweep |
| Odia | Odia | Odisha |
| Punjabi | Gurmukhi | Punjab |
| Assamese | Bengali | Assam |
| Urdu | Nastaliq | J&K |
| Nepali | Devanagari | Sikkim |

### Search categories

Each language has ~150 heat-related search terms organized into 10 categories:

- **Weather** -- heatwave, scorching heat, hot winds (loo), heat spell
- **Health** -- heatstroke, heat death, dehydration, sunstroke
- **Water** -- water crisis, drought, water shortage, tanker
- **Power** -- power cut, load shedding, blackout, grid failure
- **Agriculture** -- crop damage, livestock death, fodder shortage
- **Labor** -- outdoor worker deaths, construction heat stress
- **Governance** -- heat advisory, heat action plan, IMD red alert
- **Infrastructure** -- road melting, railway track buckling, forest fire
- **Education** -- school closure, exam postponed, summer vacation extended
- **Temperature** -- mercury soars, record temperature, degrees Celsius

## News Sources

| Source | Type | Rate Limit | Languages | API Key Required |
|--------|------|-----------|-----------|-----------------|
| **Google News** | RSS feed | ~1.5 req/sec | All 14 | No |
| **NewsData.io** | REST API | 200 req/day (free) | All 14 | Yes |
| **GNews** | REST API | 100 req/day (free) | 8 of 14 | Yes |

Sources degrade gracefully -- if an API key is missing, that source is skipped with a warning. The pipeline never crashes due to a missing key.

## LLM Relevance Checking

Before extracting full article text (the expensive step), the pipeline checks each article's title against an LLM to determine if it's actually about heat in the correct geographic region. This typically eliminates 90%+ of false positives from keyword-based search.

**Supported providers:**

| Provider | Model | Rate | Cost |
|----------|-------|------|------|
| **OpenAI** (default) | GPT-4o-mini | 5 concurrent | Paid |
| **Gemini** | Gemini 2.0 Flash | 1 concurrent, 4s interval | Free tier |
| **Claude** | Claude Haiku | Configurable | Paid |

**Multi-LLM consensus:** Combine providers with `+` for majority-vote filtering:
```bash
LLM_PROVIDER=openai+gemini  # Article kept only if majority say "relevant"
```

**Fail-open policy:** If the LLM call fails, the article is kept (not dropped). Better to extract an irrelevant article than miss a relevant one.

### Geographic validation

The LLM prompt includes the target state and district, so it rejects articles about heat in the wrong region. For example, a Delhi heatwave article found while searching for Andaman news is correctly rejected.

### District extraction

After article text is extracted, district assignment happens in three tiers:
1. **Query context** -- Articles from single-district search batches are auto-assigned
2. **English text matching** -- Scan title + body for English district names
3. **LLM extraction** -- For remaining articles, the LLM identifies the primary district from the state's district list, working across all Indian scripts

## Reliability Features

### Circuit breakers
Each news source has an independent circuit breaker. After 5 consecutive failures, the source is disabled for 60 seconds, then tested with a single request before re-enabling. One source failing doesn't affect the others.

### Checkpoint/resume
A `.checkpoint.json` file tracks which search queries have completed. If the pipeline crashes mid-collection, the next run skips already-completed queries and resumes from where it left off. The checkpoint is deleted on successful completion.

### Rate limiting
Three layers of rate control prevent API throttling:
- **Per-second limiter** with configurable jitter
- **Rolling window limiter** (e.g., 30 requests per 15 minutes for NewsData)
- **Daily budget tracker** for free-tier APIs

### Timeout management
In CI, the pipeline splits its time budget: 80% for collection, 20% for extraction/output. This ensures output is always produced even if collection takes longer than expected.

## Setup

### Prerequisites

- Python 3.12+

### Installation

```bash
git clone https://github.com/AIDMI-DataHub/heat-news-extraction.git
cd heat-news-extraction
pip install -r requirements.txt
```

### API keys

Create a `.env` file (or set environment variables):

```bash
# Required for LLM relevance checking (default provider)
OPENAI_API_KEY=sk-proj-...

# Optional: additional news sources (pipeline works with just Google News)
NEWSDATA_API_KEY=pub_...
GNEWS_API_KEY=...

# Optional: alternative LLM providers
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

At minimum, you need `OPENAI_API_KEY` for LLM relevance checking. The pipeline can run with zero API keys (`LLM_PROVIDER=none`), but output quality will be significantly lower.

## Usage

### Run locally

```bash
# Full run -- all states, today's news
python main.py

# Specific states
python main.py --states delhi,rajasthan,bihar

# Specific source only
python main.py --states delhi --sources google

# Different LLM provider
python main.py --llm gemini

# Skip LLM entirely (faster but noisier output)
python main.py --llm none

# Custom date range
python main.py --date-range 2026-04-01:2026-04-15

# Last 48 hours
python main.py --date-range-hours 48

# Cap extraction volume
python main.py --max-articles 500

# Set timeout (for CI-like behavior)
python main.py --timeout 60
```

### Configuration precedence

CLI argument > environment variable > `.env` file > code default

### GitHub Actions (automated daily run)

The pipeline runs automatically via `.github/workflows/daily-collection.yml`:

- **Schedule:** Daily at 06:30 UTC (12:00 noon IST)
- **Manual trigger:** Available from the Actions tab
- **Timeout:** 175 minutes for the pipeline, 190 minutes for the full job
- **Output:** Committed to the `output/` directory as `data: daily collection YYYY-MM-DD`

**Required GitHub secrets:**
- `OPENAI_API_KEY`
- `NEWSDATA_API_KEY`
- `GNEWS_API_KEY`
- `GEMINI_API_KEY` (optional, for fallback or consensus mode)

## Project Structure

```
heat-news-extraction/
├── main.py                           # Pipeline entry point and orchestration
├── requirements.txt                  # Python dependencies (7 packages)
├── .env                              # API keys (gitignored)
│
├── src/
│   ├── models/
│   │   └── article.py                # ArticleRef and Article (Pydantic, frozen)
│   │
│   ├── data/
│   │   ├── india_geo.json            # 36 states/UTs, ~700 districts, languages
│   │   ├── heat_terms.json           # ~150 terms x 14 languages x 10 categories
│   │   ├── exclusion_patterns.json   # Regex filters for sports, lifestyle, etc.
│   │   ├── geo_loader.py             # Geographic data access
│   │   └── heat_terms_loader.py      # Heat term access by language/category
│   │
│   ├── sources/
│   │   ├── _protocol.py              # NewsSource protocol (duck typing)
│   │   ├── google_news.py            # Google News RSS adapter
│   │   ├── newsdata.py               # NewsData.io API adapter
│   │   └── gnews.py                  # GNews API adapter
│   │
│   ├── query/
│   │   ├── _generator.py             # Query generation from geo + heat terms
│   │   ├── _models.py                # Query and QueryResult models
│   │   ├── _scheduler.py             # Rate limiting and source scheduling
│   │   └── _executor.py              # Two-phase query execution + district tagging
│   │
│   ├── extraction/
│   │   ├── _resolver.py              # Google News URL redirect resolution
│   │   └── _extractor.py             # HTML -> text via trafilatura
│   │
│   ├── relevance/
│   │   ├── _prompt.py                # Shared LLM prompts (geographic validation)
│   │   ├── _base.py                  # Abstract checker (batching, rate limiting)
│   │   ├── _openai.py                # GPT-4o-mini implementation
│   │   ├── _gemini.py                # Gemini Flash implementation
│   │   ├── _claude.py                # Claude Haiku implementation
│   │   └── _consensus.py             # Multi-LLM majority vote
│   │
│   ├── dedup/
│   │   ├── _url_dedup.py             # URL normalization and dedup
│   │   ├── _title_dedup.py           # Cosine similarity title dedup
│   │   ├── _relevance.py             # Relevance scoring + exclusion filtering
│   │   └── _title_relevance.py       # Title-based relevance checks
│   │
│   ├── reliability/
│   │   ├── _circuit_breaker.py       # Per-source circuit breaker
│   │   ├── _retry.py                 # Exponential backoff retry for rate limits
│   │   └── _checkpoint.py            # Crash recovery checkpoint store
│   │
│   └── output/
│       ├── _writers.py               # Async JSON/CSV writers (aiofiles)
│       └── _metadata.py              # Collection metadata model
│
├── tests/
│   ├── test_dedup.py                 # URL/title deduplication tests
│   └── test_relevance.py             # Relevance checker tests
│
├── output/                           # Generated daily (committed by CI)
│   ├── {state-slug}/
│   │   └── {YYYY-MM-DD}/
│   │       ├── articles.json
│   │       ├── articles.csv
│   │       └── {district-slug}/
│   │           ├── articles.json
│   │           └── articles.csv
│   └── _metadata.json
│
└── .github/
    └── workflows/
        └── daily-collection.yml      # Daily cron + manual trigger
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| httpx | 0.28.1 | Async HTTP client for all API calls |
| feedparser | 6.0.11 | Google News RSS parsing |
| trafilatura | 2.0.0 | HTML article text extraction |
| pydantic | 2.10.6 | Data validation and models |
| tenacity | 9.0.0 | Retry with exponential backoff |
| aiofiles | 24.1.0 | Async file I/O for output |
| python-dotenv | 1.1.0 | `.env` file loading |

## Tests

```bash
pip install pytest
pytest tests/
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `STATES` | all | Comma-separated state slugs (e.g., `delhi,bihar`) |
| `DISTRICTS` | all | Comma-separated district slugs |
| `SOURCES` | `google,newsdata,gnews` | Which news sources to query |
| `DATE_RANGE` | today | `YYYY-MM-DD:YYYY-MM-DD` date range |
| `DATE_RANGE_HOURS` | - | Hours lookback (overrides DATE_RANGE) |
| `MAX_ARTICLES` | `5000` | Extraction cap |
| `LLM_PROVIDER` | `openai` | `openai`, `gemini`, `claude`, `none`, or combined (e.g., `openai+gemini`) |
| `TIMEOUT_MINUTES` | `0` (no limit) | Pipeline timeout in minutes |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `GEMINI_API_KEY` | - | Google Gemini API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `NEWSDATA_API_KEY` | - | NewsData.io API key |
| `GNEWS_API_KEY` | - | GNews API key |
