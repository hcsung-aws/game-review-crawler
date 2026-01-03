"""
Property-Based Test: Search Cache Consistency

**Feature: community-crawler-enhancement, Property 12: Search Cache Consistency**
**Validates: Requirements 7.3, 7.4**

Property 12: Search Cache Consistency
*For any* 검색 쿼리에 대해, 캐시에 유효한 결과가 있으면 캐시된 결과를 반환하고,
만료되었거나 없으면 새로운 검색을 수행해야 한다.
"""

import pytest
import time
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from crawler.search.cache import SearchCache
from crawler.models.data_models import SearchResult, CrawlerConfig


keyword_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    ),
    min_size=1,
    max_size=20
).filter(lambda x: len(x.strip()) > 0)

keywords_strategy = st.lists(keyword_strategy, min_size=1, max_size=5)

site_strategy = st.sampled_from([
    "inven.co.kr",
    "ruliweb.com",
    "dcinside.com",
    "gamemeca.com",
    "example.com"
])

search_result_strategy = st.builds(
    SearchResult,
    url=st.text(min_size=10, max_size=100).map(
        lambda x: "https://example.com/" + x
    ),
    title=st.text(min_size=1, max_size=100),
    snippet=st.text(min_size=0, max_size=500),
    relevance_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)

search_results_strategy = st.lists(search_result_strategy, min_size=0, max_size=10)


class TestSearchCacheConsistencyProperty:
    """Property 12: Search Cache Consistency"""

    @given(
        keywords=keywords_strategy,
        site=site_strategy,
        results=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_cache_hit_returns_cached_results(
        self, keywords: list, site: str, results: list
    ):
        """캐시에 유효한 결과가 있으면 캐시된 결과를 반환해야 한다."""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(keywords, site, results)
        cached_results = cache.get(keywords, site)

        assert cached_results is not None
        assert len(cached_results) == len(results)

        for original, cached in zip(results, cached_results):
            assert original.url == cached.url
            assert original.title == cached.title
            assert original.snippet == cached.snippet

    @given(
        keywords=keywords_strategy,
        site=site_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_cache_miss_returns_none(self, keywords: list, site: str):
        """캐시에 결과가 없으면 None을 반환해야 한다."""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        result = cache.get(keywords, site)

        assert result is None

    @given(
        keywords=keywords_strategy,
        site=site_strategy,
        results=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_expired_cache_returns_none(
        self, keywords: list, site: str, results: list
    ):
        """캐시가 만료되면 None을 반환해야 한다."""
        config = CrawlerConfig(cache_ttl=0)
        cache = SearchCache(config)

        cache.set(keywords, site, results)
        time.sleep(0.01)
        cached_results = cache.get(keywords, site)

        assert cached_results is None

    @given(
        keywords=keywords_strategy,
        site=site_strategy,
        results1=search_results_strategy,
        results2=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_cache_update_replaces_old_results(
        self, keywords: list, site: str, results1: list, results2: list
    ):
        """동일한 쿼리에 대해 캐시를 갱신하면 새로운 결과로 대체되어야 한다."""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(keywords, site, results1)
        cache.set(keywords, site, results2)
        cached_results = cache.get(keywords, site)

        assert cached_results is not None
        assert len(cached_results) == len(results2)

        for original, cached in zip(results2, cached_results):
            assert original.url == cached.url
            assert original.title == cached.title

    @given(
        keywords1=keywords_strategy,
        keywords2=keywords_strategy,
        site=site_strategy,
        results1=search_results_strategy,
        results2=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_different_queries_have_separate_cache(
        self, keywords1: list, keywords2: list, site: str,
        results1: list, results2: list
    ):
        """서로 다른 쿼리는 별도의 캐시 항목을 가져야 한다."""
        assume(sorted(keywords1) != sorted(keywords2))

        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(keywords1, site, results1)
        cache.set(keywords2, site, results2)

        cached1 = cache.get(keywords1, site)
        cached2 = cache.get(keywords2, site)

        assert cached1 is not None
        assert cached2 is not None
        assert len(cached1) == len(results1)
        assert len(cached2) == len(results2)

    @given(
        keywords=keywords_strategy,
        site1=site_strategy,
        site2=site_strategy,
        results1=search_results_strategy,
        results2=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_same_keywords_different_sites_have_separate_cache(
        self, keywords: list, site1: str, site2: str,
        results1: list, results2: list
    ):
        """동일한 키워드라도 다른 사이트는 별도의 캐시 항목을 가져야 한다."""
        assume(site1 != site2)

        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(keywords, site1, results1)
        cache.set(keywords, site2, results2)

        cached1 = cache.get(keywords, site1)
        cached2 = cache.get(keywords, site2)

        assert cached1 is not None
        assert cached2 is not None
        assert len(cached1) == len(results1)
        assert len(cached2) == len(results2)

    @given(
        keywords=keywords_strategy,
        site=site_strategy,
        results=search_results_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_is_cached_reflects_cache_state(
        self, keywords: list, site: str, results: list
    ):
        """is_cached 메서드는 캐시 상태를 정확히 반영해야 한다."""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        assert not cache.is_cached(keywords, site)

        cache.set(keywords, site, results)
        assert cache.is_cached(keywords, site)

        cache.invalidate(keywords, site)
        assert not cache.is_cached(keywords, site)


class TestSearchCacheConsistencyUnit:
    """Search Cache Consistency Unit Tests"""

    def test_basic_cache_set_and_get(self):
        """기본 캐시 저장 및 조회"""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        keywords = ["test", "keyword"]
        site = "example.com"
        results = [
            SearchResult(
                url="https://example.com/1",
                title="Test Title",
                snippet="Test content",
                relevance_score=0.8
            )
        ]

        cache.set(keywords, site, results)
        cached = cache.get(keywords, site)

        assert cached is not None
        assert len(cached) == 1
        assert cached[0].url == results[0].url

    def test_cache_clear(self):
        """캐시 전체 초기화"""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(["kw1"], "site1", [])
        cache.set(["kw2"], "site2", [])

        count = cache.clear()

        assert count == 2
        assert cache.get(["kw1"], "site1") is None
        assert cache.get(["kw2"], "site2") is None

    def test_cache_stats(self):
        """캐시 통계 확인"""
        config = CrawlerConfig(cache_ttl=3600)
        cache = SearchCache(config)

        cache.set(["kw1"], "site1", [])
        cache.set(["kw2"], "site2", [])

        stats = cache.get_stats()

        assert stats["total"] == 2
        assert stats["valid"] == 2
        assert stats["expired"] == 0
        assert stats["ttl"] == 3600
