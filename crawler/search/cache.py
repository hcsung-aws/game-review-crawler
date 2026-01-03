"""
SearchCache 구현

Requirements: 7.3, 7.4
- 검색 결과 캐싱 및 TTL 관리
- 동일 쿼리 반복 시 캐시된 결과 반환
- 캐시 만료 시 새로운 검색 수행
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from crawler.models.data_models import SearchResult, CrawlerConfig


logger = logging.getLogger(__name__)


class SearchCache:
    """검색 결과 캐시
    
    Requirements: 7.3, 7.4
    - 검색 결과를 임시 저장하여 중복 요청 방지
    - TTL(Time To Live) 기반 캐시 만료 관리
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """SearchCache 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
        """
        if config is None:
            config = CrawlerConfig()
        
        self.ttl: int = config.cache_ttl  # 캐시 유효 시간 (초)
        # 캐시 저장소: {query_key: (results, cached_time)}
        self._cache: Dict[str, Tuple[List[SearchResult], datetime]] = {}
    
    def _generate_key(self, keywords: List[str], site: str) -> str:
        """검색 쿼리에 대한 캐시 키 생성
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트
            
        Returns:
            캐시 키 문자열
        """
        # 키워드 정렬하여 순서에 관계없이 동일한 키 생성
        sorted_keywords = sorted(keywords)
        query_string = f"{','.join(sorted_keywords)}:{site}"
        # MD5 해시로 키 생성 (충돌 가능성 낮음)
        return hashlib.md5(query_string.encode()).hexdigest()
    
    def get(self, keywords: List[str], site: str) -> Optional[List[SearchResult]]:
        """캐시된 검색 결과 반환
        
        Requirements: 7.3
        - 동일한 검색 쿼리가 반복되면 캐시된 결과 반환
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트
            
        Returns:
            캐시된 검색 결과. 캐시 미스 또는 만료 시 None
        """
        key = self._generate_key(keywords, site)
        
        if key not in self._cache:
            logger.debug(f"캐시 미스: keywords={keywords}, site={site}")
            return None
        
        results, cached_time = self._cache[key]
        
        # TTL 확인
        elapsed = (datetime.now() - cached_time).total_seconds()
        if elapsed > self.ttl:
            logger.debug(f"캐시 만료: keywords={keywords}, site={site}, elapsed={elapsed:.1f}s")
            del self._cache[key]
            return None
        
        logger.debug(f"캐시 히트: keywords={keywords}, site={site}, age={elapsed:.1f}s")
        return results
    
    def set(self, keywords: List[str], site: str, results: List[SearchResult]) -> None:
        """검색 결과 캐싱
        
        Requirements: 7.4
        - 새로운 검색 결과를 캐시에 저장
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트
            results: 검색 결과 목록
        """
        key = self._generate_key(keywords, site)
        self._cache[key] = (results, datetime.now())
        logger.debug(f"캐시 저장: keywords={keywords}, site={site}, count={len(results)}")
    
    def invalidate(self, keywords: List[str], site: str) -> bool:
        """특정 캐시 항목 무효화
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트
            
        Returns:
            무효화 성공 여부
        """
        key = self._generate_key(keywords, site)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"캐시 무효화: keywords={keywords}, site={site}")
            return True
        return False
    
    def clear(self) -> int:
        """전체 캐시 초기화
        
        Returns:
            삭제된 캐시 항목 수
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"캐시 전체 초기화: {count}개 항목 삭제")
        return count
    
    def cleanup_expired(self) -> int:
        """만료된 캐시 항목 정리
        
        Returns:
            삭제된 캐시 항목 수
        """
        now = datetime.now()
        expired_keys = []
        
        for key, (_, cached_time) in self._cache.items():
            elapsed = (now - cached_time).total_seconds()
            if elapsed > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"만료된 캐시 정리: {len(expired_keys)}개 항목 삭제")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, int]:
        """캐시 통계 반환
        
        Returns:
            캐시 통계 딕셔너리
        """
        now = datetime.now()
        valid_count = 0
        expired_count = 0
        
        for _, (_, cached_time) in self._cache.items():
            elapsed = (now - cached_time).total_seconds()
            if elapsed <= self.ttl:
                valid_count += 1
            else:
                expired_count += 1
        
        return {
            "total": len(self._cache),
            "valid": valid_count,
            "expired": expired_count,
            "ttl": self.ttl
        }
    
    def is_cached(self, keywords: List[str], site: str) -> bool:
        """캐시 존재 여부 확인 (만료 여부 포함)
        
        Args:
            keywords: 검색 키워드 목록
            site: 대상 사이트
            
        Returns:
            유효한 캐시 존재 여부
        """
        return self.get(keywords, site) is not None
