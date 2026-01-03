# Search Engine Module
"""
검색 엔진 모듈
- SearchCache: 검색 결과 캐싱
- SearchAdapter: 검색 어댑터 추상 클래스
- SearchEngineManager: 다중 검색 엔진 관리
"""

from crawler.search.cache import SearchCache
from crawler.search.adapters import (
    SearchAdapter,
    DuckDuckGoAdapter,
    GoogleCSEAdapter,
    DirectCrawlAdapter
)
from crawler.search.manager import SearchEngineManager

__all__ = [
    "SearchCache",
    "SearchAdapter",
    "DuckDuckGoAdapter",
    "GoogleCSEAdapter",
    "DirectCrawlAdapter",
    "SearchEngineManager"
]
