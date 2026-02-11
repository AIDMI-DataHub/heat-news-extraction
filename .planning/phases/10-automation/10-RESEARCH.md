# Phase 10: Automation - Research

**Researched:** 2026-02-11
**Domain:** GitHub Actions CI/CD -- scheduled Python workflow with auto-commit
**Confidence:** HIGH

## Summary

Phase 10 requires a GitHub Actions workflow that runs the existing `python main.py` pipeline daily on a cron schedule, completes within 45 minutes, uses only free-tier API sources, and commits the output data back to the repository. This is a well-understood problem domain with mature tooling -- GitHub Actions cron scheduling, the `actions/checkout` and `actions/setup-python` actions, and straightforward git commit/push steps.

The primary complexity lies in three areas: (1) the current `.gitignore` excludes `/output/`, so the workflow must either modify `.gitignore` or use `git add --force` to commit output files; (2) graceful handling of "nothing to commit" when the pipeline produces no new data; and (3) the 60-day inactivity auto-disable for scheduled workflows on public repositories. All three have well-documented solutions.

The pipeline is already designed for this use case -- API keys degrade gracefully via `os.environ.get()` with `None` default, the checkpoint system handles interrupted runs, and the entire pipeline is a single `python main.py` invocation.

**Primary recommendation:** Create a single `.github/workflows/daily-collection.yml` workflow file using `actions/checkout@v6`, `actions/setup-python@v6` with pip caching, and manual git commit/push commands (not a third-party action) for maximum control and transparency.

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `actions/checkout` | v6 (v6.0.2) | Clone repo in runner | Official GitHub action, handles auth token persistence for push |
| `actions/setup-python` | v6 (v6.2.0) | Install Python + cache pip | Official GitHub action with built-in pip cache support |
| `ubuntu-latest` | Ubuntu 24.04 | Runner OS | Default free-tier runner, includes Python 3.12 pre-installed, includes system `tzdata` |
| GITHUB_TOKEN | built-in | Auth for git push | Automatic, no PAT needed, scoped to repo |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `gautamkrishnar/keepalive-workflow` | v2 (v2.0.10) | Prevent 60-day auto-disable | Only if repo is public and may go inactive |
| `workflow_dispatch` | built-in | Manual trigger | Always include alongside `schedule` for testing/debugging |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual git commit/push | `stefanzweifel/git-auto-commit-action@v7` | Simpler syntax, but hides logic; commits by this action do NOT trigger downstream workflows; less control over "nothing to commit" handling |
| Manual git commit/push | `ad-m/github-push-action` | Only handles push, still need manual commit; extra dependency for no real benefit |
| `actions/setup-python` pip cache | Full venv cache via `actions/cache` | More complex setup; pip cache is sufficient for 6 small packages |

**Installation:** No additional packages needed beyond what is in `requirements.txt`. The workflow uses only built-in GitHub Actions features and official actions.

## Architecture Patterns

### Recommended File Structure

```
.github/
  workflows/
    daily-collection.yml    # The single workflow file
```

### Pattern 1: Dual-Trigger Workflow (schedule + manual)

**What:** Combine `on.schedule` with `on.workflow_dispatch` so the workflow can run both automatically and on-demand.
**When to use:** Always -- manual trigger is essential for testing and ad-hoc runs.

```yaml
# Source: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
name: Daily Heat News Collection

on:
  schedule:
    # Run daily at 06:30 UTC (12:00 noon IST)
    - cron: '30 6 * * *'
  workflow_dispatch:  # Manual trigger from Actions tab

permissions:
  contents: write  # Required for git push

jobs:
  collect:
    runs-on: ubuntu-latest
    timeout-minutes: 50  # 45 min for pipeline + 5 min buffer for setup/commit

    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        timeout-minutes: 45
        env:
          NEWSDATA_API_KEY: ${{ secrets.NEWSDATA_API_KEY }}
          GNEWS_API_KEY: ${{ secrets.GNEWS_API_KEY }}
        run: python main.py

      - name: Commit and push results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add --force output/
          git diff --cached --quiet && echo "No new data to commit" && exit 0
          git commit -m "data: daily collection $(date -u +%Y-%m-%d)"
          git push
```

### Pattern 2: Conditional Commit (skip when empty)

**What:** Check if there are staged changes before attempting to commit, to avoid workflow failure on empty data days.
**When to use:** Always -- some days may produce no new articles.

```yaml
# Source: verified community pattern, multiple sources
- name: Commit and push results
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add --force output/
    if git diff --cached --quiet; then
      echo "No changes to commit"
    else
      git commit -m "data: daily collection $(date -u +%Y-%m-%d)"
      git push
    fi
```

### Pattern 3: Secrets as Optional Environment Variables

**What:** Pass API keys from GitHub Secrets to environment variables. The pipeline already handles missing keys gracefully (`os.environ.get()` returns `None`).
**When to use:** Always -- this matches the existing pipeline design.

```yaml
# Source: https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions
env:
  NEWSDATA_API_KEY: ${{ secrets.NEWSDATA_API_KEY }}
  GNEWS_API_KEY: ${{ secrets.GNEWS_API_KEY }}
```

**Key behavior:** If secrets are not configured in the repo, `${{ secrets.X }}` resolves to an empty string, and `os.environ.get("X")` will return `""` (not `None`). The pipeline code should treat empty string the same as `None` -- this may need a minor adjustment.

### Pattern 4: Force-Add Gitignored Output

**What:** Use `git add --force output/` to stage files that are in `.gitignore`.
**When to use:** When you want to keep `/output/` in `.gitignore` for local development but still commit from CI.

```bash
# --force overrides .gitignore rules for the specified path
git add --force output/
```

**Alternative:** Remove `/output/` from `.gitignore` entirely. This is simpler but means local dev output also shows in `git status`.

### Anti-Patterns to Avoid

- **Using a PAT (Personal Access Token) when GITHUB_TOKEN suffices:** The built-in GITHUB_TOKEN can push commits. A PAT is only needed if you want the commit to trigger other workflows (which we do not).
- **Not setting `timeout-minutes`:** The default job timeout is 360 minutes (6 hours). Without an explicit timeout, a hung pipeline wastes runner minutes.
- **Committing with `--allow-empty`:** Creates noise commits on days with no data. Always check for changes first.
- **Using `git add .` or `git add -A`:** Could accidentally commit temp files, cache files, or other artifacts. Always specify the exact path (`output/`).
- **Hardcoding cron time without considering UTC:** All GitHub Actions cron schedules are in UTC. Document the IST equivalent in a comment.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python version management | Custom install scripts | `actions/setup-python@v6` | Handles caching, version resolution, PATH setup |
| Pip dependency caching | Manual `actions/cache` for pip | `setup-python` with `cache: 'pip'` | Built-in, automatic cache key from requirements.txt hash |
| Git identity for CI commits | Custom git config logic | Standard bot identity pattern | `github-actions[bot]` with email `41898282+github-actions[bot]@users.noreply.github.com` is the established convention |
| Workflow keep-alive | Custom cron job or API script | `gautamkrishnar/keepalive-workflow@v2` (if needed) | Handles the 60-day disable edge case automatically |
| Secrets management | Custom env file loading | GitHub Secrets + `${{ secrets.X }}` | Encrypted at rest, masked in logs, scoped to repo |

**Key insight:** GitHub Actions provides all the building blocks natively. The workflow file is pure YAML configuration -- no custom scripts or third-party actions are needed beyond the official `checkout` and `setup-python`.

## Common Pitfalls

### Pitfall 1: Output Directory in .gitignore

**What goes wrong:** `git add output/` silently adds nothing because `/output/` is in `.gitignore`. The commit step either fails or commits nothing.
**Why it happens:** `.gitignore` blocks `git add` for matching paths unless `--force` is used.
**How to avoid:** Use `git add --force output/` to override `.gitignore`. Alternatively, remove `/output/` from `.gitignore` and replace with more specific ignores.
**Warning signs:** Workflow succeeds but no output files appear in the repo.

### Pitfall 2: Empty String vs None for Missing Secrets

**What goes wrong:** `${{ secrets.NEWSDATA_API_KEY }}` resolves to empty string `""` when the secret is not set, but `os.environ.get("NEWSDATA_API_KEY")` returns `""` (truthy in Python), not `None`.
**Why it happens:** GitHub injects an empty string for undefined secrets. Python's `os.environ.get()` returns the env var value, which is `""`.
**How to avoid:** In the pipeline code, treat empty strings the same as `None`: `newsdata_key = os.environ.get("NEWSDATA_API_KEY") or None`. This converts `""` to `None`.
**Warning signs:** Source tries to use `""` as an API key and gets auth errors instead of gracefully skipping.

### Pitfall 3: Cron Schedule Runs in UTC Only

**What goes wrong:** Developer sets cron to `0 12 * * *` thinking it runs at noon local time, but it runs at noon UTC (5:30 PM IST).
**Why it happens:** GitHub Actions cron is always UTC. No timezone support.
**How to avoid:** Always add a comment with the IST equivalent: `cron: '30 6 * * *'  # 12:00 noon IST`.
**Warning signs:** Pipeline runs at unexpected times; API quotas reset at wrong boundaries.

### Pitfall 4: Scheduled Workflow Auto-Disabled After 60 Days

**What goes wrong:** After 60 days of no repository activity (commits, PRs, issues), GitHub silently disables scheduled workflows on public repos.
**Why it happens:** GitHub policy to save resources on abandoned repos.
**How to avoid:** Since this pipeline commits data regularly, it generates activity and self-prevents this issue. If the pipeline has an extended dry spell (no data for 60 days), add `gautamkrishnar/keepalive-workflow@v2` as a fallback.
**Warning signs:** Check the Actions tab -- disabled workflows show a yellow warning banner.

### Pitfall 5: Cron Delay (Not Running at Exact Scheduled Time)

**What goes wrong:** Workflow triggers 5-30 minutes after the scheduled cron time.
**Why it happens:** GitHub Actions cron specifies when the workflow is queued, not when it starts. During peak load, delays increase.
**How to avoid:** Accept this limitation. Do not design logic that depends on exact execution time. The pipeline already uses IST date for the output directory, which is correct.
**Warning signs:** Logs show start time later than expected.

### Pitfall 6: Job Timeout vs Step Timeout Confusion

**What goes wrong:** Setting `timeout-minutes: 45` on the job but the total job includes setup steps (checkout, pip install). The pipeline itself gets less than 45 minutes.
**Why it happens:** Job timeout includes ALL steps. Setup typically takes 1-3 minutes.
**How to avoid:** Set job timeout to ~50 minutes (45 + buffer), and set a separate step-level `timeout-minutes: 45` on the `python main.py` step specifically.
**Warning signs:** Pipeline killed during its run even though it should have had time.

### Pitfall 7: Git Push Race Condition

**What goes wrong:** If someone pushes to main between checkout and push, the push fails with "rejected (non-fast-forward)".
**Why it happens:** The workflow checked out an older commit, and the remote has advanced.
**How to avoid:** For a daily data-collection repo with minimal human activity, this is extremely unlikely. If it becomes a problem, add `git pull --rebase` before push. For now, keep it simple.
**Warning signs:** Push step fails with "non-fast-forward" error.

## Code Examples

### Complete Workflow File

```yaml
# Source: Assembled from official GitHub Actions docs
# https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
# https://github.com/actions/checkout
# https://github.com/actions/setup-python

name: Daily Heat News Collection

on:
  schedule:
    - cron: '30 6 * * *'  # 12:00 noon IST (06:30 UTC)
  workflow_dispatch:        # Allow manual trigger

permissions:
  contents: write           # Needed for git push

jobs:
  collect:
    runs-on: ubuntu-latest
    timeout-minutes: 50

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run collection pipeline
        timeout-minutes: 45
        env:
          NEWSDATA_API_KEY: ${{ secrets.NEWSDATA_API_KEY }}
          GNEWS_API_KEY: ${{ secrets.GNEWS_API_KEY }}
        run: python main.py

      - name: Commit and push results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add --force output/
          if git diff --cached --quiet; then
            echo "No new data to commit"
          else
            git commit -m "data: daily collection $(date -u +%Y-%m-%d)"
            git push
          fi
```

### Handling Empty-String Secrets in Python

```python
# Source: Standard Python pattern for GitHub Actions secret handling
# In main.py, change:
#   newsdata_key = os.environ.get("NEWSDATA_API_KEY")
# To:
newsdata_key = os.environ.get("NEWSDATA_API_KEY") or None
gnews_key = os.environ.get("GNEWS_API_KEY") or None
```

### Adding Secrets to GitHub Repository

```bash
# Source: https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions
# Via GitHub CLI (gh):
gh secret set NEWSDATA_API_KEY --body "your-api-key-here"
gh secret set GNEWS_API_KEY --body "your-api-key-here"

# Or via GitHub web UI:
# Settings > Secrets and variables > Actions > New repository secret
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `actions/checkout@v4` | `actions/checkout@v6` | Nov 2024 | Improved credential security (creds stored in separate file, not `.git/config`) |
| `actions/setup-python@v5` | `actions/setup-python@v6` | Sep 2024 | Upgraded to Node 24; requires runner v2.327.1+ |
| `ubuntu-22.04` as `ubuntu-latest` | `ubuntu-24.04` as `ubuntu-latest` | Jan 2025 | Python 3.12 pre-installed; system tzdata available |
| Third-party commit actions | Manual git commands | ongoing | Fewer dependencies, more control, no "commits don't trigger workflows" surprise |

**Deprecated/outdated:**
- `actions/checkout@v3`, `@v4`: Still work but miss security improvements in v6
- `actions/setup-python@v4`, `@v5`: Still work but v6 has Node 24 support and better caching
- `ubuntu-20.04`, `ubuntu-22.04`: Being phased out; `ubuntu-latest` now maps to `ubuntu-24.04`

## Open Questions

1. **Should `/output/` be removed from `.gitignore`?**
   - What we know: `git add --force output/` works regardless of `.gitignore`. Removing it from `.gitignore` makes the repo behavior more transparent but clutters local `git status` during development.
   - What's unclear: User preference on local dev experience vs. repo transparency.
   - Recommendation: Keep `/output/` in `.gitignore` and use `git add --force` in CI. This gives clean local dev experience while still committing from CI. Add a comment in `.gitignore` explaining the CI override.

2. **What time should the daily cron run?**
   - What we know: Cron is UTC-only. India is UTC+5:30. Pipeline collects heat news relevant to Indian states. IST noon = UTC 06:30.
   - What's unclear: Whether morning or evening collection is better for news coverage.
   - Recommendation: Default to `30 6 * * *` (noon IST). Morning allows daytime news from the current day; can be adjusted easily.

3. **Is the repo public or private?**
   - What we know: No git remote is configured yet, so we cannot determine visibility. Public repos get unlimited Actions minutes; private repos get 2000 min/month on free plan. At ~50 min/day, private would use ~1500 min/month (within free tier but tight).
   - What's unclear: User's plan for repo visibility.
   - Recommendation: Design assuming either. Document the minutes math. If private, the 50 min/day usage is within the 2000 min/month free tier but leaves little headroom.

4. **Should the `or None` fix for empty-string secrets be part of this phase?**
   - What we know: The current code uses `os.environ.get("KEY")` which returns `""` for empty env vars in CI, not `None`. This could cause API sources to attempt requests with invalid keys.
   - What's unclear: Whether existing source code already handles empty strings gracefully.
   - Recommendation: Include a small code fix in this phase: `os.environ.get("KEY") or None`. It is directly related to CI behavior and takes one line per key.

## Sources

### Primary (HIGH confidence)
- [actions/checkout releases](https://github.com/actions/checkout/releases) -- confirmed v6.0.2 is latest (Jan 2025)
- [actions/setup-python README](https://github.com/actions/setup-python) -- confirmed v6.2.0 with pip cache syntax
- [GitHub Actions workflow syntax docs](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions) -- cron syntax, timeout-minutes, permissions, env
- [GitHub Actions events that trigger workflows](https://docs.github.com/en/actions/learn-github-actions/events-that-trigger-workflows) -- schedule + workflow_dispatch combined triggers
- [GitHub Actions automatic token authentication](https://docs.github.com/en/actions/security-guides/automatic-token-authentication) -- GITHUB_TOKEN permissions for push
- [GitHub Actions using secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions) -- secrets syntax and behavior

### Secondary (MEDIUM confidence)
- [GitHub Actions usage limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration) -- free tier minutes, 6-hour job max, 60-day disable rule
- [stefanzweifel/git-auto-commit-action](https://github.com/stefanzweifel/git-auto-commit-action) -- evaluated and rejected in favor of manual git commands
- [gautamkrishnar/keepalive-workflow](https://github.com/marketplace/actions/keepalive-workflow) -- v2.0.10 for 60-day keepalive
- [runner-images Ubuntu 24.04 README](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md) -- pre-installed software on ubuntu-latest

### Tertiary (LOW confidence)
- Community discussions on cron delay (5-30 min) -- [multiple GitHub community threads](https://github.com/orgs/community/discussions/156282), consistent reports but no official SLA
- `tzdata` availability on Ubuntu 24.04 runner -- system package likely present but not explicitly confirmed in runner image docs; needs validation during first workflow run

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are official GitHub Actions with verified version numbers from release pages
- Architecture: HIGH -- the workflow pattern (cron + checkout + setup-python + run + commit) is extremely well-documented and widely used
- Pitfalls: HIGH -- all pitfalls are based on official documentation or confirmed community reports with multiple sources
- Code examples: HIGH -- assembled from official docs with verified syntax

**Research date:** 2026-02-11
**Valid until:** 2026-04-11 (60 days -- GitHub Actions is stable; action major versions change infrequently)
