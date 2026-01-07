# Utilities Package
"""유틸리티 함수 및 클래스"""

from crawler.utils.relevance_filter import RelevanceFilter
from crawler.utils.url_deduplicator import deduplicate_urls, deduplicate_search_results, normalize_url
from crawler.utils.rate_limiter import RateLimiter

__all__ = [
    "RelevanceFilter",
    "deduplicate_urls",
    "deduplicate_search_results",
    "normalize_url",
    "RateLimiter",
]

# Lazy import to avoid circular dependency
def __getattr__(name):
    if name in ("DataFilter", "FilterCriteria", "SortField", "SortOrder"):
        from crawler.utils.data_filter import DataFilter, FilterCriteria, SortField, SortOrder
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
