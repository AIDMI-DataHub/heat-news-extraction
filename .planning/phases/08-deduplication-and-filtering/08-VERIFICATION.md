---
phase: 08-deduplication-and-filtering
verified: 2026-02-11T04:10:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 8: Deduplication and Filtering Verification Report

**Phase Goal:** The pipeline removes duplicate articles and filters for genuine heat/disaster relevance while maintaining high recall

**Verified:** 2026-02-11T04:10:00Z

**Status:** passed

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each article receives a relevance_score (0.0-1.0) based on heat term presence in title + full_text and category diversity | ✓ VERIFIED | `score_relevance()` implements formula: (term_score * 0.5) + (category_score * 0.3) + title_bonus(0.2), returns 0.0-1.0. Verified via smoke test: heatwave article scored 1.00. Tests cover multiple terms, zero terms, title bonus, category diversity. |
| 2 | Articles with full_text=None still score based on title alone (baseline 0.3+ if heat terms found in title) | ✓ VERIFIED | Lines 119-120 in `_relevance.py` implement floor of 0.3 for `full_text=None` with title terms. Test `test_full_text_none_with_heat_title_scores_above_zero` verifies score >= 0.3. |
| 3 | A configurable exclusion_patterns.json exists and can be updated without code changes to add new irrelevant patterns | ✓ VERIFIED | `src/data/exclusion_patterns.json` exists with 9 patterns in JSON format. Contains version, description, and pattern array. Validated via `json.loads()`. No code changes needed to add patterns — just edit JSON. |
| 4 | Exclusion patterns are conjunctive (cricket + score, not cricket alone) to avoid removing legitimate heat articles mentioning sports venues | ✓ VERIFIED | All 9 patterns use conjunctive regex: `\bcricket\b.*\b(score|scorecard|innings|wicket|runs)\b` requires both "cricket" AND score-related terms. Test `test_keeps_article_with_heat_and_cricket` verifies heat+cricket article is kept. |
| 5 | Only articles scoring below 0.05 AND matching an exclusion pattern are filtered out (high recall -- borderline kept) | ✓ VERIFIED | Lines 148-151 in `filter_articles()`: exclude only if `score < 0.05 AND _matches_exclusion()`. Test `test_keeps_borderline_article` verifies low-score article without exclusion match is kept. Test `test_excludes_cricket_score_article` verifies cricket article is excluded. |
| 6 | The deduplicate_and_filter() pipeline function composes URL dedup -> title dedup -> score -> filter in correct order | ✓ VERIFIED | Lines 51-57 in `__init__.py`: Stage 1 URL dedup, Stage 2 title dedup (threshold=0.85), Stage 3 filter_articles. End-to-end test confirms: 6 input -> 3 output (removed 2 dups + 1 cricket). All outputs have scores > 0.0. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/data/exclusion_patterns.json` | Configurable irrelevant pattern list | ✓ VERIFIED | Exists, 16 lines, valid JSON with 9 patterns array. Contains version, description, patterns. |
| `src/dedup/_relevance.py` | score_relevance() and filter_articles() | ✓ VERIFIED | Exists, 158 lines. Exports `score_relevance`, `filter_articles`, `_load_exclusion_patterns`, `_combine_text`, `_matches_exclusion`. Implements scoring formula and high-recall filtering. |
| `src/dedup/__init__.py` | Public API: deduplicate_and_filter, re-exports | ✓ VERIFIED | Exists, 65 lines. Exports all 6 public symbols in `__all__`. Implements `deduplicate_and_filter()` composing 3 stages. |
| `tests/test_relevance.py` | Unit tests for relevance scoring and filtering | ✓ VERIFIED | Exists, 150 lines (exceeds min_lines: 60). Contains 10 tests across 2 classes: TestScoreRelevance (5 tests) and TestFilterArticles (5 tests). All tests pass. |

**Artifact Status:** 4/4 artifacts verified (exist, substantive, wired)

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/dedup/_relevance.py` | `src/data/heat_terms_loader.py` | imports get_terms_by_category and TERM_CATEGORIES | ✓ WIRED | Line 19: `from src.data.heat_terms_loader import TERM_CATEGORIES, get_terms_by_category`. Used in `score_relevance()` line 99-104 for term matching. |
| `src/dedup/_relevance.py` | `src/data/exclusion_patterns.json` | loads exclusion patterns from JSON file | ✓ WIRED | Line 35: Path construction to `exclusion_patterns.json`. Line 37: `json.loads(data_path.read_text())`. Patterns compiled and returned. |
| `src/dedup/_relevance.py` | `src/models/article.py` | imports Article, uses model_copy(update=) for frozen model | ✓ WIRED | Line 20: `from src.models.article import Article`. Line 145: `article.model_copy(update={"relevance_score": score})`. Correctly handles frozen Pydantic model. |
| `src/dedup/__init__.py` | `src/dedup/_url_dedup.py` | imports deduplicate_by_url | ✓ WIRED | Line 19: `from src.dedup._url_dedup import deduplicate_by_url, normalize_url`. Used in line 51: `deduped_url = deduplicate_by_url(articles)`. |
| `src/dedup/__init__.py` | `src/dedup/_title_dedup.py` | imports deduplicate_by_title | ✓ WIRED | Line 18: `from src.dedup._title_dedup import deduplicate_by_title`. Used in line 54: `deduped_title = deduplicate_by_title(deduped_url, threshold=0.85)`. |
| `src/dedup/__init__.py` | `src/dedup/_relevance.py` | imports score_relevance, filter_articles | ✓ WIRED | Line 17: `from src.dedup._relevance import filter_articles, score_relevance`. Used in line 57: `filtered = filter_articles(deduped_title)`. Also re-exported in `__all__`. |

**Link Status:** 6/6 key links verified (all wired)

### Requirements Coverage

No requirements explicitly mapped to Phase 08 in REQUIREMENTS.md. Phase goal aligns with general data quality requirements.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, no empty implementations, no console.log-only functions. All commits verified in git log.

### Human Verification Required

None. All observable truths are programmatically verified. Pipeline behavior is deterministic and covered by automated tests.

---

## Summary

Phase 8 goal **ACHIEVED**. All 6 observable truths verified against actual codebase:

1. ✓ Relevance scoring formula implemented: term presence (50%) + category diversity (30%) + title bonus (20%)
2. ✓ Articles with full_text=None get 0.3 floor when title has heat terms
3. ✓ Configurable exclusion_patterns.json with 9 conjunctive patterns
4. ✓ Conjunctive patterns preserve legitimate heat articles mentioning sports/entertainment
5. ✓ High-recall filtering: exclude only if score < 0.05 AND exclusion match
6. ✓ deduplicate_and_filter() composes URL dedup -> title dedup -> score -> filter

**Evidence:**
- 4 artifacts exist and substantive (exclusion_patterns.json, _relevance.py, __init__.py, test_relevance.py)
- All 6 key links wired correctly (imports verified, usage verified)
- 30 tests pass (20 dedup + 10 relevance)
- End-to-end pipeline test: 6 articles -> 3 articles (removed 2 duplicates + 1 cricket article)
- All output articles have relevance_score > 0.0
- All 3 commits from SUMMARY verified in git log (c085a23, b7baa14, 1c8c1b6)

**Next Phase Readiness:** Downstream phases can import `from src.dedup import deduplicate_and_filter` and call with `list[Article]` to get deduplicated, scored, and filtered results. Pipeline maintains high recall by keeping borderline articles.

---

_Verified: 2026-02-11T04:10:00Z_
_Verifier: Claude (gsd-verifier)_
