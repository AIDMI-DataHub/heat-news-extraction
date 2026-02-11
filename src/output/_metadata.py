"""Collection-level metadata model for output traceability.

Captures information about a single collection run: when it happened,
which sources and query terms were used, and article counts at each
pipeline stage.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionMetadata(BaseModel):
    """Frozen metadata describing a single collection run.

    Written alongside per-state article files to provide
    traceability and auditing of each pipeline execution.
    """

    model_config = ConfigDict(frozen=True)

    collection_timestamp: datetime
    sources_queried: list[str]
    query_terms_used: list[str]
    counts: dict[str, int]
