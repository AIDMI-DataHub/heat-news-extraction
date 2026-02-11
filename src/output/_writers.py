"""Async JSON and CSV output writers for collected articles.

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


async def write_json(
    articles: list[Article],
    output_dir: Path,
    state_slug: str,
) -> Path:
    """Write articles as a JSON file under output_dir/state_slug/.

    Creates the directory on write (OUTP-03). Uses ensure_ascii=False
    to preserve Indian language scripts in output (OUTP-04).

    Returns the path to the written JSON file.
    """
    dest = output_dir / state_slug
    dest.mkdir(parents=True, exist_ok=True)

    data = {
        "state": articles[0].state if articles else state_slug,
        "date": output_dir.name,
        "article_count": len(articles),
        "articles": [a.model_dump(mode="json") for a in articles],
    }

    text = json.dumps(data, indent=2, ensure_ascii=False)
    path = dest / "articles.json"

    async with aiofiles.open(path, "w", encoding="utf-8") as fh:
        await fh.write(text)

    return path


async def write_csv(
    articles: list[Article],
    output_dir: Path,
    state_slug: str,
) -> Path:
    """Write articles as a CSV file under output_dir/state_slug/.

    Uses a StringIO bridge pattern: builds CSV in an in-memory buffer
    with csv.DictWriter, then writes the result via aiofiles.
    Includes full_text in CSV to match JSON structure (OUTP-02).

    Returns the path to the written CSV file.
    """
    dest = output_dir / state_slug
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


async def write_collection_output(
    articles: list[Article],
    output_dir: Path,
    metadata: CollectionMetadata,
) -> dict[str, list[Path]]:
    """Write all articles grouped by state, plus collection metadata.

    Groups articles by a slug derived from article.state, then writes
    JSON and CSV files for each state in parallel. Also writes a
    _metadata.json file at the output_dir root.

    Returns a dict with keys "json", "csv", "metadata" mapping to
    lists of written file paths.
    """
    # Group articles by state slug
    groups: dict[str, list[Article]] = {}
    for article in articles:
        slug = (
            article.state.lower()
            .replace(" ", "-")
            .replace("&", "and")
        )
        groups.setdefault(slug, []).append(article)

    # Write JSON + CSV per state in parallel
    tasks: list[tuple[str, asyncio.Task[Path]]] = []
    async with asyncio.TaskGroup() as tg:
        for slug, group in groups.items():
            json_task = tg.create_task(write_json(group, output_dir, slug))
            csv_task = tg.create_task(write_csv(group, output_dir, slug))
            tasks.append(("json", json_task))
            tasks.append(("csv", csv_task))

    json_paths = [t.result() for kind, t in tasks if kind == "json"]
    csv_paths = [t.result() for kind, t in tasks if kind == "csv"]

    # Write collection metadata
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = output_dir / "_metadata.json"
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
