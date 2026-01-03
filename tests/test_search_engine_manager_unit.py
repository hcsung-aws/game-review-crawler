"""
Unit test: SearchEngineManager 검색 및 필터링

**Validates: Requirements 3.1, 3.2**

SearchEngineManager의 검색 결과 필터링 동작을 검증한다.
- 관련성 점수 계산 및 필터링
- threshold 기반 결과 필터링
"""

import pytest
from typing import List

from crawler.search.manager import SearchEngineManager
from crawler.search.adapters import SearchAdapter
from crawler.models.data_models import SearchResult, CrawlerConfig


class MockSearchAdapter(SearchAdapter):
    """테스트용 Mock 검색 어댑터"""
    
    def __init__(self, adapter_name: str, results: List[SearchResult] = None):
        self._name = adapter_name
        self._results = results or []
        self._available = True
    
    @property
    def name(self) -> str:
        return self._name
    
    def is_available(self) -> bool:
        return self._available
    
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        return self._results[:max_results]
    
    def reset_throttle(self) -> None:
        pass


class TestSearchEngineManagerFiltering:
    """SearchEngineManager 검색 결과 필터링 테스트
    
    Requirements: 3.1, 3.2
    - 관련성 점수 계산
    - threshold 기반 필터링
    """
    
    def test_filter_results_by_relevance_threshold(self):
        """관련성 점수가 threshold 미만인 결과는 필터링됨
        
        Requirements: 3.2
        - Relevance_Score가 0.5 미만인 결과는 제외
        """
        # 키워드가 포함된 결과와 포함되지 않은 결과 생성
        results = [
            SearchResult(
                url="https://example.com/1",
                title="몬스터헌터 월드 리뷰",  # 키워드 포함
                snippet="몬스터헌터 월드는 훌륭한 게임입니다",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="전혀 관련없는 게시글",  # 키워드 미포함
                snippet="이것은 관련없는 내용입니다",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/3",
                title="몬스터헌터 공략",  # 키워드 포함
                snippet="몬스터헌터 공략 가이드",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.5)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        # 검색 수행 (필터링 활성화)
        filtered_results = manager.search(
            keywords=["몬스터헌터"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        # 키워드가 포함된 결과만 반환되어야 함
        assert len(filtered_results) == 2
        for result in filtered_results:
            assert result.relevance_score >= 0.5
            assert "몬스터헌터" in result.title or "몬스터헌터" in result.snippet
    
    def test_all_results_filtered_when_no_keyword_match(self):
        """키워드가 전혀 매칭되지 않으면 모든 결과가 필터링됨
        
        Requirements: 3.2
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="관련없는 게시글 1",
                snippet="전혀 다른 내용",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="관련없는 게시글 2",
                snippet="또 다른 내용",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.5)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        filtered_results = manager.search(
            keywords=["몬스터헌터", "리뷰"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        # 모든 결과가 필터링되어 빈 리스트 반환
        assert len(filtered_results) == 0
    
    def test_relevance_score_calculated_for_each_result(self):
        """각 결과에 대해 관련성 점수가 계산됨
        
        Requirements: 3.1
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="게임 리뷰",
                snippet="재미있는 게임입니다",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="게임 공략",
                snippet="게임 공략 가이드",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.0)  # 모든 결과 포함
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        filtered_results = manager.search(
            keywords=["게임"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        # 모든 결과에 점수가 계산되어야 함
        assert len(filtered_results) == 2
        for result in filtered_results:
            assert result.relevance_score > 0.0
            assert 0.0 <= result.relevance_score <= 1.0
    
    def test_filter_disabled_returns_all_results(self):
        """필터링 비활성화 시 모든 결과 반환
        
        apply_filter=False일 때 필터링 없이 모든 결과 반환
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="관련없는 게시글",
                snippet="전혀 다른 내용",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="또 다른 게시글",
                snippet="또 다른 내용",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.5)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        # 필터링 비활성화
        all_results = manager.search(
            keywords=["몬스터헌터"],
            site="example.com",
            use_cache=False,
            apply_filter=False
        )
        
        # 모든 결과가 반환되어야 함
        assert len(all_results) == 2
    
    def test_custom_threshold_applied(self):
        """사용자 정의 threshold가 적용됨
        
        Requirements: 3.2
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="몬스터헌터 월드 리뷰 평가",  # 키워드 많이 포함
                snippet="몬스터헌터 월드 리뷰입니다",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="몬스터헌터",  # 키워드 적게 포함
                snippet="간단한 내용",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        
        # 높은 threshold 설정
        config = CrawlerConfig(relevance_threshold=0.7)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        filtered_results = manager.search(
            keywords=["몬스터헌터", "리뷰"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        # 높은 threshold로 인해 일부 결과만 반환
        for result in filtered_results:
            assert result.relevance_score >= 0.7
    
    def test_multiple_keywords_improve_relevance(self):
        """여러 키워드 매칭 시 관련성 점수 향상
        
        Requirements: 3.1, 3.3
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="몬스터헌터 월드 리뷰",  # 2개 키워드 매칭
                snippet="몬스터헌터 월드 리뷰입니다",
                relevance_score=0.0
            ),
            SearchResult(
                url="https://example.com/2",
                title="몬스터헌터 공략",  # 1개 키워드 매칭
                snippet="공략 가이드",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.0)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        filtered_results = manager.search(
            keywords=["몬스터헌터", "리뷰"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        # 두 결과 모두 반환
        assert len(filtered_results) == 2
        
        # 더 많은 키워드가 매칭된 결과가 더 높은 점수를 가져야 함
        result_with_more_keywords = next(
            r for r in filtered_results if "리뷰" in r.title
        )
        result_with_fewer_keywords = next(
            r for r in filtered_results if "리뷰" not in r.title
        )
        
        assert result_with_more_keywords.relevance_score >= result_with_fewer_keywords.relevance_score
    
    def test_empty_results_handled_gracefully(self):
        """빈 검색 결과 처리
        
        검색 결과가 없을 때 빈 리스트 반환
        """
        adapter = MockSearchAdapter("TestAdapter", [])
        manager = SearchEngineManager()
        manager.register_adapter(adapter)
        
        results = manager.search(
            keywords=["테스트"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        assert results == []
    
    def test_relevance_score_range(self):
        """관련성 점수가 0.0 ~ 1.0 범위 내에 있음
        
        Requirements: 3.1
        """
        results = [
            SearchResult(
                url="https://example.com/1",
                title="테스트 키워드 테스트 키워드 테스트",  # 키워드 많이 반복
                snippet="테스트 테스트 테스트 테스트 테스트",
                relevance_score=0.0
            ),
        ]
        
        adapter = MockSearchAdapter("TestAdapter", results)
        config = CrawlerConfig(relevance_threshold=0.0)
        manager = SearchEngineManager(config)
        manager.register_adapter(adapter)
        
        filtered_results = manager.search(
            keywords=["테스트", "키워드"],
            site="example.com",
            use_cache=False,
            apply_filter=True
        )
        
        assert len(filtered_results) == 1
        assert 0.0 <= filtered_results[0].relevance_score <= 1.0
