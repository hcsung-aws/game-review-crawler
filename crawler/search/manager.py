"""
SearchEngineManager 구현

Requirements: 7.1, 7.2
- 다중 검색 어댑터 관리
- Failover 메커니즘
- SearchCache 통합
"""

import logging
from typing import List, Optional

from crawler.models.data_models import SearchResult, CrawlerConfig
from crawler.search.cache import SearchCache
from crawler.search.adapters import SearchAdapter
from crawler.utils.relevance_filter import RelevanceFilter


logger = logging.getLogger(__name__)


class SearchEngineManager:
    """다중 검색 엔진 관리자
    
    Requirements: 7.1, 7.2
    - 다양한 검색 어댑터를 관리하고 통일된 인터페이스 제공
    - 어댑터 실패 시 자동으로 다음 어댑터로 failover
    - 검색 결과 캐싱 지원
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """SearchEngineManager 초기화
        
        Args:
            config: 크롤러 설정
        """
        self._config = config or CrawlerConfig()
        self._adapters: List[SearchAdapter] = []
        self._cache = SearchCache(self._config)
        self._relevance_filter = RelevanceFilter()
        self._current_adapter_index = 0
    
    def register_adapter(self, adapter: SearchAdapter) -> None:
        """검색 어댑터 등록
        
        Args:
            adapter: 등록할 검색 어댑터
        """
        self._adapters.append(adapter)
        logger.info(f"검색 어댑터 등록: {adapter.name}")
    
    def get_adapters(self) -> List[SearchAdapter]:
        """등록된 어댑터 목록 반환
        
        Returns:
            어댑터 목록
        """
        return self._adapters.copy()
    
    def get_available_adapters(self) -> List[SearchAdapter]:
        """사용 가능한 어댑터 목록 반환
        
        Returns:
            사용 가능한 어댑터 목록
        """
        return [a for a in self._adapters if a.is_available()]
    
    def search(
        self, 
        keywords: List[str], 
        site: str, 
        max_results: int = 10,
        use_cache: bool = True,
        apply_filter: bool = True
    ) -> List[SearchResult]:
        """검색 수행
        
        Requirements: 7.1, 7.2, 7.3
        - 캐시 확인 후 검색 수행
        - 실패 시 다음 어댑터로 failover
        - 관련성 필터링 적용
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            use_cache: 캐시 사용 여부
            apply_filter: 관련성 필터 적용 여부
            
        Returns:
            검색 결과 목록
            
        Raises:
            RuntimeError: 모든 어댑터 실패 시
        """
        if not self._adapters:
            raise RuntimeError("등록된 검색 어댑터가 없습니다.")
        
        # 캐시 확인
        if use_cache:
            cached_results = self._cache.get(keywords, site)
            if cached_results is not None:
                logger.info(f"캐시 히트: keywords={keywords}, site={site}")
                return cached_results
        
        # Failover 검색 수행
        results = self._failover_search(keywords, site, max_results)
        
        # 관련성 점수 계산 및 필터링
        if apply_filter and results:
            results = self._apply_relevance_filter(results, keywords)
        
        # 캐시 저장
        if use_cache and results:
            self._cache.set(keywords, site, results)
        
        return results
    
    def _failover_search(
        self, 
        keywords: List[str], 
        site: str, 
        max_results: int
    ) -> List[SearchResult]:
        """Failover 검색 수행
        
        Requirements: 7.2
        - 현재 어댑터 실패 시 다음 어댑터로 전환
        - 모든 어댑터 시도 후 실패하면 예외 발생
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트 도메인
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
            
        Raises:
            RuntimeError: 모든 어댑터 실패 시
        """
        errors = []
        tried_adapters = []
        
        # 현재 인덱스부터 시작하여 모든 어댑터 시도
        for i in range(len(self._adapters)):
            adapter_index = (self._current_adapter_index + i) % len(self._adapters)
            adapter = self._adapters[adapter_index]
            
            if not adapter.is_available():
                logger.debug(f"어댑터 사용 불가: {adapter.name}")
                continue
            
            tried_adapters.append(adapter.name)
            
            try:
                logger.info(f"검색 시도: {adapter.name}")
                results = adapter.search(keywords, site, max_results)
                
                # 성공 시 현재 어댑터 인덱스 업데이트
                self._current_adapter_index = adapter_index
                return results
                
            except Exception as e:
                error_msg = f"{adapter.name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"검색 실패, failover 시도: {error_msg}")
        
        # 모든 어댑터 실패
        if not tried_adapters:
            raise RuntimeError("사용 가능한 검색 어댑터가 없습니다.")
        
        error_summary = "; ".join(errors)
        raise RuntimeError(f"모든 검색 어댑터 실패: {error_summary}")
    
    def _apply_relevance_filter(
        self, 
        results: List[SearchResult], 
        keywords: List[str]
    ) -> List[SearchResult]:
        """관련성 필터 적용
        
        Requirements: 3.1, 3.2
        - 각 결과에 관련성 점수 계산
        - threshold 이상의 결과만 반환
        
        Args:
            results: 검색 결과 목록
            keywords: 검색 키워드 목록
            
        Returns:
            필터링된 검색 결과 목록
        """
        # 필터링 적용 (filter 메서드 내에서 점수 계산도 수행)
        threshold = self._config.relevance_threshold
        filtered = self._relevance_filter.filter(results, keywords, threshold)
        
        logger.info(
            f"관련성 필터링: {len(results)}개 → {len(filtered)}개 "
            f"(threshold={threshold})"
        )
        
        return filtered
    
    def clear_cache(self) -> int:
        """캐시 초기화
        
        Returns:
            삭제된 캐시 항목 수
        """
        return self._cache.clear()
    
    def get_cache_stats(self) -> dict:
        """캐시 통계 반환
        
        Returns:
            캐시 통계 딕셔너리
        """
        return self._cache.get_stats()
    
    def reset_adapters(self) -> None:
        """모든 어댑터 상태 초기화"""
        self._current_adapter_index = 0
        for adapter in self._adapters:
            if hasattr(adapter, 'reset_throttle'):
                adapter.reset_throttle()
        logger.info("모든 어댑터 상태 초기화")
