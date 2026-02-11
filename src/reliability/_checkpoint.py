"""Checkpoint store for crash recovery in the heat news extraction pipeline.

Tracks completed query keys (SHA-256 hashes of query fields) and persists
them to a JSON file via ``aiofiles``.  On restart, the pipeline loads the
checkpoint and skips already-completed queries.

Uses ``TYPE_CHECKING`` guard for the Query import to avoid circular imports
(same pattern as ``src/query/_scheduler.py``).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

if TYPE_CHECKING:
    from src.query._models import Query

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Saves and loads checkpoint state for crash recovery.

    Args:
        checkpoint_path: Path to the JSON checkpoint file.  Parent
            directories are created automatically on :meth:`save`.
    """

    def __init__(self, checkpoint_path: Path) -> None:
        self._path = checkpoint_path
        self._completed: set[str] = set()

    # -- Query key generation -------------------------------------------------

    @staticmethod
    def query_key(q: Query) -> str:
        """Compute a stable key for *q* using SHA-256 of its fields.

        The key is a 16-character hex string derived from
        ``source_hint|state_slug|language|level|query_string``.
        """
        raw = (
            f"{q.source_hint}|{q.state_slug}|{q.language}"
            f"|{q.level}|{q.query_string}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # -- Completion tracking --------------------------------------------------

    def is_completed(self, q: Query) -> bool:
        """Return True if *q* has already been completed."""
        return self.query_key(q) in self._completed

    async def mark_completed(self, q: Query) -> None:
        """Mark *q* as completed (add its key to the set)."""
        self._completed.add(self.query_key(q))

    # -- Persistence ----------------------------------------------------------

    async def save(self) -> None:
        """Persist the checkpoint to disk as JSON via aiofiles."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"completed_queries": sorted(self._completed)}
        async with aiofiles.open(self._path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2))
        logger.debug(
            "Checkpoint saved: %d completed queries -> %s",
            len(self._completed),
            self._path,
        )

    async def load(self) -> None:
        """Load checkpoint from disk if the file exists."""
        if self._path.exists():
            async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
                raw = await f.read()
            data = json.loads(raw)
            self._completed = set(data.get("completed_queries", []))
            logger.info(
                "Checkpoint loaded: %d completed queries from %s",
                len(self._completed),
                self._path,
            )

    # -- Properties -----------------------------------------------------------

    @property
    def completed_count(self) -> int:
        """Return the number of completed queries."""
        return len(self._completed)
