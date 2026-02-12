"""Async JSON and CSV output writers for collected articles.

Output structure:
    output/
      state-slug/
        YYYY-MM-DD/
          articles.json        -- state-level articles
          articles.csv
          district-slug/
            articles.json      -- district-level articles
            articles.csv
      _metadata.json

Directories are created upfront from geographic data. Articles are
placed into the correct state/date/district folder based on their
own metadata (article.state, article.date, article.district).

All file I/O uses aiofiles to avoid blocking the event loop.
Indian language scripts (Devanagari, Tamil, etc.) are preserved
via ensure_ascii=False in JSON output.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
from pathlib import Path

import aiofiles

from src.models.article import Article
from src.output._metadata import CollectionMetadata


def _slugify(name: str) -> str:
    """Convert a state or district name to a filesystem-safe slug."""
    return name.lower().replace(" ", "-").replace("&", "and")


def create_output_directories(
    output_root: Path,
    regions: list | None = None,
) -> None:
    """Create the directory skeleton from geographic data.

    Creates state-level directories for all regions. District
    subdirectories are created on-demand when articles are written
    (since date folders vary per run).

    Args:
        output_root: Root output directory (e.g. Path("output")).
        regions: List of StateUT objects. If None, creates only the root.
    """
    output_root.mkdir(parents=True, exist_ok=True)

    if regions is None:
        return

    for region in regions:
        state_dir = output_root / region.slug
        state_dir.mkdir(exist_ok=True)


async def _write_json(articles: list[Article], dest: Path) -> Path:
    """Write articles as a JSON file at dest/articles.json."""
    dest.mkdir(parents=True, exist_ok=True)

    data = {
        "state": articles[0].state if articles else "",
        "district": articles[0].district if articles and articles[0].district else None,
        "date": _get_date_str(articles[0]) if articles else "",
        "article_count": len(articles),
        "articles": [a.model_dump(mode="json") for a in articles],
    }

    text = json.dumps(data, indent=2, ensure_ascii=False)
    path = dest / "articles.json"

    async with aiofiles.open(path, "w", encoding="utf-8") as fh:
        await fh.write(text)

    return path


async def _write_csv(articles: list[Article], dest: Path) -> Path:
    """Write articles as a CSV file at dest/articles.csv."""
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "articles.csv"

    if not articles:
        async with aiofiles.open(path, "w", encoding="utf-8") as fh:
            await fh.write("")
        return path

    fieldnames = list(articles[0].model_dump(mode="json").keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for article in articles:
        writer.writerow(article.model_dump(mode="json"))

    async with aiofiles.open(path, "w", encoding="utf-8") as fh:
        await fh.write(buf.getvalue())

    return path


def _get_date_str(article: Article) -> str:
    """Extract YYYY-MM-DD date string from an article's date."""
    return article.date.strftime("%Y-%m-%d")


# Keep old function signatures working for backwards compatibility
async def write_json(
    articles: list[Article],
    output_dir: Path,
    state_slug: str,
) -> Path:
    """Write articles as a JSON file under output_dir/state_slug/."""
    return await _write_json(articles, output_dir / state_slug)


async def write_csv(
    articles: list[Article],
    output_dir: Path,
    state_slug: str,
) -> Path:
    """Write articles as a CSV file under output_dir/state_slug/."""
    return await _write_csv(articles, output_dir / state_slug)


async def write_collection_output(
    articles: list[Article],
    output_root: Path,
    metadata: CollectionMetadata,
    date_str: str = "",
) -> dict[str, list[Path]]:
    """Write all articles grouped by state, date, and district.

    Each article is placed based on its own metadata:
    - article.state -> state directory slug
    - article.date  -> YYYY-MM-DD date directory
    - article.district -> district subdirectory (if set)

    Output structure:
        output_root/
          state-slug/
            YYYY-MM-DD/
              articles.json       -- state-level articles
              articles.csv
              district-slug/
                articles.json     -- district-level articles
                articles.csv
          _metadata.json

    Args:
        articles: All articles to write.
        output_root: Root output directory (e.g. Path("output")).
        metadata: Collection metadata to write.
        date_str: Unused, kept for backwards compatibility.

    Returns:
        Dict with keys "json", "csv", "metadata" mapping to lists
        of written file paths.
    """
    # Group articles by (state_slug, date_str, district_slug or None)
    groups: dict[tuple[str, str, str | None], list[Article]] = {}
    for article in articles:
        state_slug = _slugify(article.state)
        article_date = _get_date_str(article)
        district_slug = _slugify(article.district) if article.district else None
        key = (state_slug, article_date, district_slug)
        groups.setdefault(key, []).append(article)

    # Write JSON + CSV per group in parallel
    tasks: list[tuple[str, asyncio.Task[Path]]] = []

    async with asyncio.TaskGroup() as tg:
        for (state_slug, art_date, district_slug), group in groups.items():
            if district_slug:
                dest = output_root / state_slug / art_date / district_slug
            else:
                dest = output_root / state_slug / art_date

            json_task = tg.create_task(_write_json(group, dest))
            csv_task = tg.create_task(_write_csv(group, dest))
            tasks.append(("json", json_task))
            tasks.append(("csv", csv_task))

    json_paths = [t.result() for kind, t in tasks if kind == "json"]
    csv_paths = [t.result() for kind, t in tasks if kind == "csv"]

    # Write collection metadata at root
    output_root.mkdir(parents=True, exist_ok=True)
    meta_path = output_root / "_metadata.json"
    meta_text = json.dumps(
        metadata.model_dump(mode="json"),
        indent=2,
        ensure_ascii=False,
    )

    async with aiofiles.open(meta_path, "w", encoding="utf-8") as fh:
        await fh.write(meta_text)

    return {
        "json": json_paths,
        "csv": csv_paths,
        "metadata": [meta_path],
    }
