"""Output writers for the heat news extraction pipeline.

This sub-package holds JSON and CSV output writers for persisting
collected articles and extraction results to disk.
"""

from src.output._metadata import CollectionMetadata
from src.output._writers import (
    create_output_directories,
    write_collection_output,
    write_csv,
    write_json,
)

__all__ = [
    "CollectionMetadata",
    "create_output_directories",
    "write_collection_output",
    "write_csv",
    "write_json",
]
