"""
RateLimiter 구현

Requirements: 5.1, 5.2, 5.3, 5.4
- 도메인별 요청 속도 제어
- 지수 백오프 처리
- 도메인별 개별 설정 지원
"""

import time
import random
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from crawler.models.data_models import CrawlerConfig


logger = logging.getLogger(__name__)


class RateLimiter:
    """도메인별 요청 속도 제어 및 지수 백오프 처리
    
    Requirements:
    - 5.1: 동일 도메인에 최소 3초 간격 유지
    - 5.2: HTTP 429 응답 시 지수 백오프 방식으로 재시도
    - 5.3: 재시도 횟수가 3회 초과 시 해당 도메인 크롤링 일시 중단
    - 5.4: 도메인별로 개별 설정 적용 가능
    - 8.1: 요청 간격에 랜덤 지연(Jitter) 추가
    - 8.2: 설정된 범위 내에서 무작위 시간 추가
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        """RateLimiter 초기화
        
        Args:
            config: 크롤러 설정. None이면 기본값 사용
        """
        if config is None:
            config = CrawlerConfig()
        
        self.default_delay: float = config.default_delay
        self.max_retries: int = config.max_retries
        self.jitter_range: Tuple[float, float] = config.jitter_range
        
        # Jitter 활성화 여부 (기본값: True)
        self._jitter_enabled: bool = True
        
        # 도메인별 설정
        self._domain_delays: Dict[str, float] = {}
        # 도메인별 마지막 요청 시간
        self._last_request_time: Dict[str, float] = {}
        # 도메인별 현재 재시도 횟수
        self._retry_counts: Dict[str, int] = {}
        # 도메인별 일시 중단 상태
        self._suspended_domains: Dict[str, bool] = {}
    
    def _extract_domain(self, url_or_domain: str) -> str:
        """URL 또는 도메인에서 도메인 추출
        
        Args:
            url_or_domain: URL 또는 도메인 문자열
            
        Returns:
            도메인 문자열
        """
        if url_or_domain.startswith(('http://', 'https://')):
            parsed = urlparse(url_or_domain)
            return parsed.netloc
        return url_or_domain
    
    def set_domain_delay(self, domain: str, delay: float) -> None:
        """도메인별 지연 시간 설정
        
        Requirements: 5.4
        
        Args:
            domain: 도메인 문자열
            delay: 지연 시간 (초)
        """
        domain = self._extract_domain(domain)
        self._domain_delays[domain] = delay
        logger.debug(f"도메인 '{domain}' 지연 시간 설정: {delay}초")
    
    def set_jitter_range(self, jitter_min: float, jitter_max: float) -> None:
        """Jitter 범위 설정
        
        Requirements: 8.2
        
        Args:
            jitter_min: 최소 jitter 값 (초)
            jitter_max: 최대 jitter 값 (초)
            
        Raises:
            ValueError: jitter_min이 음수이거나 jitter_max보다 큰 경우
        """
        if jitter_min < 0:
            raise ValueError("jitter_min은 0 이상이어야 합니다.")
        if jitter_min > jitter_max:
            raise ValueError("jitter_min은 jitter_max보다 작거나 같아야 합니다.")
        
        self.jitter_range = (jitter_min, jitter_max)
        logger.debug(f"Jitter 범위 설정: ({jitter_min}, {jitter_max})초")
    
    def set_jitter_enabled(self, enabled: bool) -> None:
        """Jitter 활성화/비활성화 설정
        
        Args:
            enabled: True면 jitter 활성화, False면 비활성화
        """
        self._jitter_enabled = enabled
        logger.debug(f"Jitter {'활성화' if enabled else '비활성화'}")
    
    def is_jitter_enabled(self) -> bool:
        """Jitter 활성화 여부 반환
        
        Returns:
            Jitter 활성화 여부
        """
        return self._jitter_enabled
    
    def get_delay_for_domain(self, domain: str) -> float:
        """도메인의 지연 시간 반환
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            해당 도메인의 지연 시간 (초)
        """
        domain = self._extract_domain(domain)
        return self._domain_delays.get(domain, self.default_delay)
    
    def _add_jitter(self, base_delay: float) -> float:
        """기본 지연에 랜덤 지연(Jitter) 추가
        
        Requirements: 8.1, 8.2
        - 요청 간격에 랜덤 지연(Jitter) 추가
        - 설정된 범위 내에서 무작위 시간 추가
        
        Args:
            base_delay: 기본 지연 시간 (초)
            
        Returns:
            Jitter가 추가된 지연 시간 (초)
            반환값은 항상 base_delay + jitter_min 이상,
            base_delay + jitter_max 이하
        """
        jitter_min, jitter_max = self.jitter_range
        jitter = random.uniform(jitter_min, jitter_max)
        return base_delay + jitter
    
    def get_jitter_range(self) -> Tuple[float, float]:
        """현재 Jitter 범위 반환
        
        Returns:
            (jitter_min, jitter_max) 튜플
        """
        return self.jitter_range
    
    def wait(self, domain: str) -> float:
        """도메인별 대기 시간 적용 (Jitter 포함)
        
        Requirements: 5.1, 8.1, 8.2
        - 동일 도메인에 연속 요청 시 최소 지연 시간 유지
        - 요청 간격에 랜덤 지연(Jitter) 추가
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            실제 대기한 시간 (초). 도메인이 중단된 경우 -1 반환
        """
        domain = self._extract_domain(domain)
        
        # 도메인이 일시 중단 상태인지 확인
        if self._suspended_domains.get(domain, False):
            logger.warning(f"도메인 '{domain}'이 일시 중단 상태입니다.")
            return -1.0
        
        # 해당 도메인의 지연 시간 가져오기
        base_delay = self.get_delay_for_domain(domain)
        
        # Jitter 적용 (활성화된 경우)
        if self._jitter_enabled:
            effective_delay = self._add_jitter(base_delay)
        else:
            effective_delay = base_delay
        
        # 마지막 요청 시간 확인
        current_time = time.time()
        last_time = self._last_request_time.get(domain, 0)
        elapsed = current_time - last_time
        
        # 필요한 대기 시간 계산
        if elapsed < effective_delay:
            wait_time = effective_delay - elapsed
        else:
            wait_time = 0
        
        # 실제 대기
        if wait_time > 0:
            logger.debug(f"도메인 '{domain}' 대기: {wait_time:.2f}초 (base: {base_delay:.2f}, jitter: {self._jitter_enabled})")
            time.sleep(wait_time)
        
        # 마지막 요청 시간 갱신
        self._last_request_time[domain] = time.time()
        
        return wait_time
    
    def handle_rate_limit(self, domain: str) -> Tuple[bool, float]:
        """HTTP 429 응답 시 지수 백오프 처리
        
        Requirements: 5.2, 5.3
        - 지수 백오프 방식으로 재시도
        - 재시도 횟수가 max_retries 초과 시 해당 도메인 일시 중단
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            (재시도 가능 여부, 대기 시간) 튜플
            재시도 불가능한 경우 대기 시간은 0
        """
        domain = self._extract_domain(domain)
        
        # 현재 재시도 횟수 증가
        current_retry = self._retry_counts.get(domain, 0) + 1
        self._retry_counts[domain] = current_retry
        
        # 최대 재시도 횟수 초과 확인
        if current_retry > self.max_retries:
            logger.warning(
                f"도메인 '{domain}' 재시도 횟수 초과 ({current_retry}/{self.max_retries}). "
                "해당 도메인 크롤링을 일시 중단합니다."
            )
            self._suspended_domains[domain] = True
            return (False, 0.0)
        
        # 지수 백오프 계산: 2^(retry_count) 초
        backoff_delay = 2 ** current_retry
        
        logger.info(
            f"도메인 '{domain}' Rate limit 발생. "
            f"재시도 {current_retry}/{self.max_retries}, "
            f"대기 시간: {backoff_delay}초"
        )
        
        # 실제 대기
        time.sleep(backoff_delay)
        
        # 마지막 요청 시간 갱신
        self._last_request_time[domain] = time.time()
        
        return (True, backoff_delay)
    
    def reset_retry_count(self, domain: str) -> None:
        """도메인의 재시도 횟수 초기화
        
        성공적인 요청 후 호출하여 재시도 카운터를 리셋
        
        Args:
            domain: 도메인 문자열
        """
        domain = self._extract_domain(domain)
        self._retry_counts[domain] = 0
    
    def resume_domain(self, domain: str) -> None:
        """일시 중단된 도메인 재개
        
        Args:
            domain: 도메인 문자열
        """
        domain = self._extract_domain(domain)
        self._suspended_domains[domain] = False
        self._retry_counts[domain] = 0
        logger.info(f"도메인 '{domain}' 크롤링 재개")
    
    def is_domain_suspended(self, domain: str) -> bool:
        """도메인이 일시 중단 상태인지 확인
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            일시 중단 상태 여부
        """
        domain = self._extract_domain(domain)
        return self._suspended_domains.get(domain, False)
    
    def get_retry_count(self, domain: str) -> int:
        """도메인의 현재 재시도 횟수 반환
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            현재 재시도 횟수
        """
        domain = self._extract_domain(domain)
        return self._retry_counts.get(domain, 0)
    
    def get_last_request_time(self, domain: str) -> Optional[float]:
        """도메인의 마지막 요청 시간 반환
        
        Args:
            domain: 도메인 문자열
            
        Returns:
            마지막 요청 시간 (Unix timestamp). 요청 기록이 없으면 None
        """
        domain = self._extract_domain(domain)
        return self._last_request_time.get(domain)
