"""
URL 중복 제거 유틸리티

Requirements: 3.4
- 중복 URL이 발견되면 해당 URL을 한 번만 처리
- 원본에 있던 모든 고유 URL이 결과에 포함
"""

from typing import List
from urllib.parse import urlparse, urlunparse
from crawler.models.data_models import SearchResult


def normalize_url(url: str) -> str:
    """URL을 정규화하여 비교 가능한 형태로 변환
    
    Args:
        url: 정규화할 URL
        
    Returns:
        정규화된 URL 문자열
    """
    try:
        parsed = urlparse(url.strip().lower())
        # 스킴, 호스트, 경로만 사용 (쿼리 파라미터, 프래그먼트 제외 가능)
        # 여기서는 전체 URL을 정규화
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),  # 후행 슬래시 제거
            parsed.params,
            parsed.query,
            ''  # 프래그먼트 제거
        ))
        return normalized
    except Exception:
        return url.strip().lower()


def deduplicate_urls(urls: List[str]) -> List[str]:
    """URL 목록에서 중복을 제거
    
    Args:
        urls: URL 문자열 목록
        
    Returns:
        중복이 제거된 URL 목록 (원본 순서 유지)
        
    Requirements: 3.4
    - 중복 URL이 발견되면 첫 번째 것만 유지
    - 원본에 있던 모든 고유 URL이 결과에 포함
    """
    seen = set()
    result = []
    
    for url in urls:
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)  # 원본 URL 유지
    
    return result


def deduplicate_search_results(results: List[SearchResult]) -> List[SearchResult]:
    """SearchResult 목록에서 URL 기준으로 중복 제거
    
    Args:
        results: SearchResult 객체 목록
        
    Returns:
        중복이 제거된 SearchResult 목록 (원본 순서 유지)
        
    Requirements: 3.4
    - 중복 URL이 발견되면 첫 번째 것만 유지
    - 원본에 있던 모든 고유 URL이 결과에 포함
    """
    seen = set()
    result = []
    
    for search_result in results:
        normalized = normalize_url(search_result.url)
        if normalized not in seen:
            seen.add(normalized)
            result.append(search_result)
    
    return result
