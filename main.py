"""Heat News Extraction Pipeline - single entry point.

This is the main entry point for the heat news extraction pipeline.
It collects heat-related news articles from across all Indian states,
union territories, and districts in 14+ local languages using free-tier
news APIs and RSS feeds.

Usage:
    python main.py
"""

import asyncio

# Core third-party dependencies
import httpx
import feedparser
import trafilatura
import pydantic
import tenacity
import aiofiles

# Pipeline sub-packages
from src import sources, models, extraction, output


async def main() -> None:
    """Run the heat news extraction pipeline."""
    print("Heat News Extraction Pipeline")
    print("=" * 40)
    print(f"  httpx:        {httpx.__version__}")
    print(f"  pydantic:     {pydantic.__version__}")
    print(f"  trafilatura:  {trafilatura.__version__}")
    print("=" * 40)
    print("Pipeline modules loaded: sources, models, extraction, output")
    print("Ready. (No tasks configured yet -- pipeline stages will be added in subsequent phases.)")


if __name__ == "__main__":
    asyncio.run(main())
