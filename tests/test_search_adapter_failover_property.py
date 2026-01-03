"""
Property test: Search Adapter Failover

**Feature: community-crawler-enhancement, Property 11: Search Adapter Failover**
**Validates: Requirements 7.2**

*For any* 검색 어댑터 목록과 실패 패턴에 대해,
*When* 첫 번째 어댑터가 실패하면,
*Then* 다음 어댑터로 자동 failover되어 검색이 수행되어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import MagicMock, patch
from typing import List

from crawler.search.manager import SearchEngineManager
from crawler.search.adapters import SearchAdapter
from crawler.models.data_models import SearchResult, CrawlerConfig


class MockSearchAdapter(SearchAdapter):
    """테스트용 Mock 검색 어댑터"""
    
    def __init__(self, adapter_name: str, should_fail: bool = False, available: bool = True):
        self._name = adapter_name
        self._should_fail = should_fail
        self._available = available
        self._search_count = 0
    
    @property
    def name(self) -> str:
        return self._name
    
    def is_available(self) -> bool:
        return self._available
    
    def search(self, keywords: List[str], site: str, max_results: int = 10) -> List[SearchResult]:
        self._search_count += 1
        if self._should_fail:
            raise RuntimeError(f"{self._name} 검색 실패")
        return [
            SearchResult(
                url=f"https://{site}/post/{i}",
                title=f"{' '.join(keywords)} 관련 게시글 {i}",
                snippet=f"테스트 snippet {i}",
                relevance_score=0.5
            )
            for i in range(min(max_results, 3))
        ]
    
    def reset_throttle(self) -> None:
        pass


# Strategies
adapter_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
).filter(lambda x: x.strip() != "")

keyword_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=30
).filter(lambda x: x.strip() != "")

site_strategy = st.sampled_from(["inven.co.kr", "ruliweb.com", "dcinside.com", "example.com"])


class TestSearchAdapterFailoverProperty:
    """Search Adapter Failover Property Tests"""
    
    @given(
        adapter_names=st.lists(adapter_name_strategy, min_size=2, max_size=5, unique=True),
        keywords=st.lists(keyword_strategy, min_size=1, max_size=3),
        site=site_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_failover_to_next_adapter_on_failure(
        self, adapter_names: List[str], keywords: List[str], site: str
    ):
        """Property: 첫 번째 어댑터 실패 시 다음 어댑터로 failover
        
        *For any* N개의 어댑터 중 첫 번째가 실패하면,
        *Then* 두 번째 어댑터가 호출되어야 한다.
        """
        # 유효한 키워드만 사용
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        assume(len(keywords) > 0)
        assume(len(adapter_names) >= 2)
        
        # 어댑터 생성: 첫 번째 어댑터만 실패, 나머지는 성공
        adapters = []
        for i, name in enumerate(adapter_names):
            should_fail = (i == 0)  # 첫 번째 어댑터만 실패
            adapters.append(MockSearchAdapter(name, should_fail=should_fail))
        
        # SearchEngineManager 설정
        manager = SearchEngineManager()
        for adapter in adapters:
            manager.register_adapter(adapter)
        
        # 검색 수행 (캐시 비활성화, 필터 비활성화)
        results = manager.search(keywords, site, use_cache=False, apply_filter=False)
        
        # 검증: 결과가 반환되어야 함
        assert len(results) > 0, "Failover 후 결과가 반환되어야 함"
        
        # 검증: 첫 번째 어댑터(실패)는 호출되었어야 함
        assert adapters[0]._search_count == 1, "첫 번째 어댑터(실패)도 호출되어야 함"
        
        # 검증: 두 번째 어댑터(성공)가 호출되어야 함
        assert adapters[1]._search_count == 1, "두 번째 어댑터가 failover로 호출되어야 함"
        
        # 검증: 세 번째 이후 어댑터는 호출되지 않아야 함 (두 번째가 성공했으므로)
        for i in range(2, len(adapters)):
            assert adapters[i]._search_count == 0, f"어댑터 {i}는 호출되면 안 됨"
    
    @given(
        adapter_count=st.integers(min_value=2, max_value=5),
        keywords=st.lists(keyword_strategy, min_size=1, max_size=3),
        site=site_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_all_adapters_fail_raises_error(
        self, adapter_count: int, keywords: List[str], site: str
    ):
        """Property: 모든 어댑터 실패 시 RuntimeError 발생
        
        *For any* 모든 어댑터가 실패하면,
        *Then* RuntimeError가 발생해야 한다.
        """
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        assume(len(keywords) > 0)
        
        # 모든 어댑터가 실패하도록 설정
        adapters = [
            MockSearchAdapter(f"Adapter{i}", should_fail=True)
            for i in range(adapter_count)
        ]
        
        manager = SearchEngineManager()
        for adapter in adapters:
            manager.register_adapter(adapter)
        
        # 모든 어댑터 실패 시 RuntimeError 발생
        with pytest.raises(RuntimeError) as exc_info:
            manager.search(keywords, site, use_cache=False, apply_filter=False)
        
        assert "모든 검색 어댑터 실패" in str(exc_info.value)
        
        # 모든 어댑터가 시도되었는지 확인
        for adapter in adapters:
            assert adapter._search_count == 1, f"{adapter.name}이 호출되어야 함"
    
    @given(
        adapter_count=st.integers(min_value=1, max_value=5),
        unavailable_indices=st.lists(st.integers(min_value=0), min_size=0, max_size=3),
        keywords=st.lists(keyword_strategy, min_size=1, max_size=3),
        site=site_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_skip_unavailable_adapters(
        self, adapter_count: int, unavailable_indices: List[int], keywords: List[str], site: str
    ):
        """Property: 사용 불가능한 어댑터는 건너뛰어야 함
        
        *For any* 일부 어댑터가 사용 불가능하면,
        *Then* 해당 어댑터는 건너뛰고 다음 어댑터를 시도해야 한다.
        """
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        assume(len(keywords) > 0)
        
        # unavailable_indices를 유효 범위로 조정
        unavailable_set = {idx % adapter_count for idx in unavailable_indices}
        
        # 최소 하나의 어댑터는 사용 가능해야 함
        assume(len(unavailable_set) < adapter_count)
        
        adapters = []
        for i in range(adapter_count):
            available = i not in unavailable_set
            adapters.append(MockSearchAdapter(f"Adapter{i}", should_fail=False, available=available))
        
        manager = SearchEngineManager()
        for adapter in adapters:
            manager.register_adapter(adapter)
        
        results = manager.search(keywords, site, use_cache=False, apply_filter=False)
        
        # 결과가 반환되어야 함
        assert len(results) > 0
        
        # 사용 불가능한 어댑터는 호출되지 않아야 함
        for i in unavailable_set:
            assert adapters[i]._search_count == 0, f"사용 불가능한 {adapters[i].name}은 호출되면 안 됨"
        
        # 사용 가능한 어댑터 중 하나는 호출되어야 함
        available_called = any(
            adapters[i]._search_count > 0 
            for i in range(adapter_count) 
            if i not in unavailable_set
        )
        assert available_called, "사용 가능한 어댑터가 호출되어야 함"
    
    @given(
        keywords=st.lists(keyword_strategy, min_size=1, max_size=3),
        site=site_strategy
    )
    @settings(max_examples=20, deadline=None)
    def test_no_adapters_raises_error(self, keywords: List[str], site: str):
        """Property: 어댑터가 없으면 RuntimeError 발생
        
        *For any* 등록된 어댑터가 없으면,
        *Then* RuntimeError가 발생해야 한다.
        """
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        assume(len(keywords) > 0)
        
        manager = SearchEngineManager()
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.search(keywords, site, use_cache=False, apply_filter=False)
        
        assert "등록된 검색 어댑터가 없습니다" in str(exc_info.value)
    
    @given(
        adapter_count=st.integers(min_value=2, max_value=4),
        success_index=st.integers(min_value=0),
        keywords=st.lists(keyword_strategy, min_size=1, max_size=3),
        site=site_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_failover_order_preserved(
        self, adapter_count: int, success_index: int, keywords: List[str], site: str
    ):
        """Property: Failover 순서가 등록 순서대로 유지됨
        
        *For any* 어댑터 목록에서,
        *Then* failover는 등록 순서대로 시도되어야 한다.
        """
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        assume(len(keywords) > 0)
        
        success_index = success_index % adapter_count
        
        # success_index 이전의 어댑터는 실패, 이후는 성공
        adapters = []
        for i in range(adapter_count):
            should_fail = (i < success_index)
            adapters.append(MockSearchAdapter(f"Adapter{i}", should_fail=should_fail))
        
        manager = SearchEngineManager()
        for adapter in adapters:
            manager.register_adapter(adapter)
        
        results = manager.search(keywords, site, use_cache=False, apply_filter=False)
        
        assert len(results) > 0
        
        # success_index 이전의 어댑터는 모두 호출되어야 함
        for i in range(success_index):
            assert adapters[i]._search_count == 1, f"Adapter{i}가 호출되어야 함"
        
        # success_index 어댑터는 호출되어야 함
        assert adapters[success_index]._search_count == 1
        
        # success_index 이후의 어댑터는 호출되지 않아야 함
        for i in range(success_index + 1, adapter_count):
            assert adapters[i]._search_count == 0, f"Adapter{i}는 호출되면 안 됨"


class TestSearchAdapterFailoverUnit:
    """Search Adapter Failover Unit Tests"""
    
    def test_single_adapter_success(self):
        """단일 어댑터 성공 케이스"""
        adapter = MockSearchAdapter("TestAdapter", should_fail=False)
        manager = SearchEngineManager()
        manager.register_adapter(adapter)
        
        results = manager.search(["테스트"], "example.com", use_cache=False, apply_filter=False)
        
        assert len(results) > 0
        assert adapter._search_count == 1
    
    def test_failover_with_two_adapters(self):
        """두 어댑터 failover 케이스"""
        adapter1 = MockSearchAdapter("Adapter1", should_fail=True)
        adapter2 = MockSearchAdapter("Adapter2", should_fail=False)
        
        manager = SearchEngineManager()
        manager.register_adapter(adapter1)
        manager.register_adapter(adapter2)
        
        results = manager.search(["테스트"], "example.com", use_cache=False, apply_filter=False)
        
        assert len(results) > 0
        assert adapter1._search_count == 1
        assert adapter2._search_count == 1
    
    def test_all_unavailable_raises_error(self):
        """모든 어댑터가 사용 불가능한 경우"""
        adapter1 = MockSearchAdapter("Adapter1", available=False)
        adapter2 = MockSearchAdapter("Adapter2", available=False)
        
        manager = SearchEngineManager()
        manager.register_adapter(adapter1)
        manager.register_adapter(adapter2)
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.search(["테스트"], "example.com", use_cache=False, apply_filter=False)
        
        assert "사용 가능한 검색 어댑터가 없습니다" in str(exc_info.value)
