"""
RelevanceFilter Property-Based Tests

Property-based testing using Hypothesis library.
Each test runs minimum 100 iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from crawler.utils.relevance_filter import RelevanceFilter
from crawler.models.data_models import SearchResult


# 키워드 생성 전략: 비어있지 않은 문자열 리스트 (ASCII 문자만 사용하여 생성 속도 향상)
keyword_strategy = st.lists(
    st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=1, max_size=10),
    min_size=1,
    max_size=3
)

# 콘텐츠 생성 전략 (ASCII 문자만 사용)
content_strategy = st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')), min_size=0, max_size=200)

# 제목 생성 전략 (ASCII 문자만 사용)
title_strategy = st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')), min_size=0, max_size=50)

# URL 생성 전략
url_strategy = st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=1, max_size=30).map(lambda x: f"https://example.com/{x}")

# threshold 생성 전략 (0.0 ~ 1.0)
threshold_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


class TestRelevanceScoreRangeAndFiltering:
    """
    # **Feature: community-crawler-enhancement, Property 3: Relevance Score Range and Filtering**
    
    *For any* 검색 결과와 키워드 목록에 대해, 계산된 Relevance_Score는 0.0 이상 1.0 이하이며,
    필터링 후 결과는 모두 threshold 이상의 점수를 가져야 한다.
    
    **Validates: Requirements 3.1, 3.2**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(
        content=content_strategy,
        title=title_strategy,
        keywords=keyword_strategy
    )
    def test_relevance_score_is_within_range(self, content: str, title: str, keywords: list):
        """관련성 점수는 항상 0.0 이상 1.0 이하여야 한다"""
        relevance_filter = RelevanceFilter()
        score = relevance_filter.calculate_score(content, keywords, title)
        
        assert 0.0 <= score <= 1.0, f"Score {score} is out of range [0.0, 1.0]"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(
        results=st.lists(
            st.builds(
                SearchResult,
                url=url_strategy,
                title=title_strategy,
                snippet=content_strategy,
                relevance_score=st.just(0.0)
            ),
            min_size=0,
            max_size=10
        ),
        keywords=keyword_strategy,
        threshold=threshold_strategy
    )
    def test_filtered_results_meet_threshold(self, results: list, keywords: list, threshold: float):
        """필터링된 결과는 모두 threshold 이상의 점수를 가져야 한다"""
        relevance_filter = RelevanceFilter()
        filtered = relevance_filter.filter(results, keywords, threshold)
        
        for result in filtered:
            assert result.relevance_score >= threshold, \
                f"Result score {result.relevance_score} is below threshold {threshold}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(
        results=st.lists(
            st.builds(
                SearchResult,
                url=url_strategy,
                title=title_strategy,
                snippet=content_strategy,
                relevance_score=st.just(0.0)
            ),
            min_size=0,
            max_size=10
        ),
        keywords=keyword_strategy,
        threshold=threshold_strategy
    )
    def test_all_filtered_scores_are_in_range(self, results: list, keywords: list, threshold: float):
        """필터링된 모든 결과의 점수는 0.0 ~ 1.0 범위 내에 있어야 한다"""
        relevance_filter = RelevanceFilter()
        filtered = relevance_filter.filter(results, keywords, threshold)
        
        for result in filtered:
            assert 0.0 <= result.relevance_score <= 1.0, \
                f"Filtered result score {result.relevance_score} is out of range [0.0, 1.0]"



class TestKeywordFrequencyAffectsScore:
    """
    # **Feature: community-crawler-enhancement, Property 4: Keyword Frequency Affects Score**
    
    *For any* 두 개의 콘텐츠 A와 B에서, A가 B보다 키워드를 더 많이 포함하면
    A의 Relevance_Score는 B 이상이어야 한다.
    
    **Validates: Requirements 3.3**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(
        base_content=st.text(min_size=0, max_size=100),
        keyword=st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=1, max_size=10),
        extra_count=st.integers(min_value=1, max_value=10)
    )
    def test_more_keywords_means_higher_or_equal_score(self, base_content: str, keyword: str, extra_count: int):
        """키워드가 더 많이 포함된 콘텐츠는 더 높거나 같은 점수를 가져야 한다"""
        keyword = keyword.strip()
        if not keyword:
            return  # 빈 키워드는 스킵
        
        relevance_filter = RelevanceFilter()
        keywords = [keyword]
        
        # 콘텐츠 A: base_content에 키워드 추가
        content_a = base_content + (" " + keyword) * extra_count
        
        # 콘텐츠 B: base_content만 (키워드 없음 또는 적음)
        content_b = base_content
        
        score_a = relevance_filter.calculate_score(content_a, keywords)
        score_b = relevance_filter.calculate_score(content_b, keywords)
        
        assert score_a >= score_b, \
            f"Content with more keywords should have higher or equal score. " \
            f"Score A ({score_a}) < Score B ({score_b})"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    @given(
        keyword=st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=1, max_size=10),
        count_a=st.integers(min_value=1, max_value=20),
        count_b=st.integers(min_value=0, max_value=20)
    )
    def test_keyword_frequency_ordering(self, keyword: str, count_a: int, count_b: int):
        """키워드 빈도가 높은 콘텐츠가 낮은 콘텐츠보다 점수가 높거나 같아야 한다"""
        keyword = keyword.strip()
        if not keyword:
            return
        
        relevance_filter = RelevanceFilter()
        keywords = [keyword]
        
        # count_a >= count_b가 되도록 정렬
        if count_a < count_b:
            count_a, count_b = count_b, count_a
        
        content_high = (keyword + " ") * count_a
        content_low = (keyword + " ") * count_b
        
        score_high = relevance_filter.calculate_score(content_high, keywords)
        score_low = relevance_filter.calculate_score(content_low, keywords)
        
        assert score_high >= score_low, \
            f"Higher frequency ({count_a}) should have >= score than lower ({count_b}). " \
            f"Got {score_high} < {score_low}"



from crawler.utils.url_deduplicator import deduplicate_urls, deduplicate_search_results, normalize_url


class TestURLDeduplication:
    """
    # **Feature: community-crawler-enhancement, Property 5: URL Deduplication**
    
    *For any* URL 목록에 대해, 중복 제거 후 결과의 모든 URL은 고유해야 하며,
    원본에 있던 모든 고유 URL이 결과에 포함되어야 한다.
    
    **Validates: Requirements 3.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        urls=st.lists(
            st.text(min_size=1, max_size=50).map(lambda x: f"https://example.com/{x}"),
            min_size=0,
            max_size=20
        )
    )
    def test_deduplicated_urls_are_unique(self, urls: list):
        """중복 제거 후 모든 URL은 고유해야 한다"""
        result = deduplicate_urls(urls)
        
        # 정규화된 URL들이 모두 고유한지 확인
        normalized_results = [normalize_url(url) for url in result]
        assert len(normalized_results) == len(set(normalized_results)), \
            "Deduplicated URLs should all be unique"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        urls=st.lists(
            st.text(min_size=1, max_size=50).map(lambda x: f"https://example.com/{x}"),
            min_size=0,
            max_size=20
        )
    )
    def test_all_unique_urls_preserved(self, urls: list):
        """원본의 모든 고유 URL이 결과에 포함되어야 한다"""
        result = deduplicate_urls(urls)
        
        # 원본의 고유 URL 집합
        original_unique = set(normalize_url(url) for url in urls)
        # 결과의 URL 집합
        result_set = set(normalize_url(url) for url in result)
        
        assert original_unique == result_set, \
            "All unique URLs from original should be in result"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        results=st.lists(
            st.builds(
                SearchResult,
                url=st.text(min_size=1, max_size=50).map(lambda x: f"https://example.com/{x}"),
                title=title_strategy,
                snippet=content_strategy,
                relevance_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
            ),
            min_size=0,
            max_size=20
        )
    )
    def test_search_results_deduplicated_urls_are_unique(self, results: list):
        """SearchResult 중복 제거 후 모든 URL은 고유해야 한다"""
        deduplicated = deduplicate_search_results(results)
        
        normalized_urls = [normalize_url(r.url) for r in deduplicated]
        assert len(normalized_urls) == len(set(normalized_urls)), \
            "Deduplicated SearchResult URLs should all be unique"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        results=st.lists(
            st.builds(
                SearchResult,
                url=st.text(min_size=1, max_size=50).map(lambda x: f"https://example.com/{x}"),
                title=title_strategy,
                snippet=content_strategy,
                relevance_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
            ),
            min_size=0,
            max_size=20
        )
    )
    def test_search_results_all_unique_urls_preserved(self, results: list):
        """SearchResult의 모든 고유 URL이 결과에 포함되어야 한다"""
        deduplicated = deduplicate_search_results(results)
        
        original_unique = set(normalize_url(r.url) for r in results)
        result_set = set(normalize_url(r.url) for r in deduplicated)
        
        assert original_unique == result_set, \
            "All unique URLs from original SearchResults should be in result"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        urls=st.lists(
            st.text(min_size=1, max_size=50).map(lambda x: f"https://example.com/{x}"),
            min_size=0,
            max_size=20
        )
    )
    def test_result_size_less_than_or_equal_to_original(self, urls: list):
        """중복 제거 결과의 크기는 원본 이하여야 한다"""
        result = deduplicate_urls(urls)
        
        assert len(result) <= len(urls), \
            "Deduplicated result should not be larger than original"
