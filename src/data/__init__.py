"""Geographic and reference data for the heat news extraction pipeline."""

from .geo_loader import (
    District,
    GeoData,
    StateUT,
    get_all_regions,
    get_all_states,
    get_all_uts,
    get_districts_for_region,
    get_languages_for_region,
    get_region_by_slug,
    load_geo_data,
)

__all__ = [
    "District",
    "GeoData",
    "StateUT",
    "get_all_regions",
    "get_all_states",
    "get_all_uts",
    "get_districts_for_region",
    "get_languages_for_region",
    "get_region_by_slug",
    "load_geo_data",
]
