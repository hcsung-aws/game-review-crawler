"""
RateLimiter Property-Based Tests

Property-based testing using Hypothesis library.
Each test runs minimum 100 iterations.
"""

import time
from unittest.mock import patch
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from crawler.utils.rate_limiter import RateLimiter
from crawler.models.data_models import CrawlerConfig


# 도메인 생성 전략
domain_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
).map(lambda x: f"{x}.com")

# URL 생성 전략
url_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
).map(lambda x: f"https://{x}.com/path")

# 지연 시간 전략 (테스트 속도를 위해 작은 값 사용)
delay_strategy = st.floats(min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False)

# 재시도 횟수 전략
retry_count_strategy = st.integers(min_value=1, max_value=5)


class TestRateLimiterMinimumDelay:
    """
    # **Feature: community-crawler-enhancement, Property 7: Rate Limiter Minimum Delay**
    
    *For any* 동일 도메인에 대한 연속 요청에서, 두 요청 사이의 시간 간격은
    설정된 최소 지연 시간 이상이어야 한다.
    
    **Validates: Requirements 5.1**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        delay=delay_strategy
    )
    def test_consecutive_requests_respect_minimum_delay(self, domain: str, delay: float):
        """연속 요청 사이의 시간 간격은 최소 지연 시간 이상이어야 한다"""
        config = CrawlerConfig(default_delay=delay)
        rate_limiter = RateLimiter(config)
        # Jitter 비활성화하여 정확한 지연 시간 테스트
        rate_limiter.set_jitter_enabled(False)
        
        # 첫 번째 요청
        rate_limiter.wait(domain)
        first_request_time = time.time()
        
        # 두 번째 요청
        rate_limiter.wait(domain)
        second_request_time = time.time()
        
        elapsed = second_request_time - first_request_time
        
        # 시간 측정 오차를 고려하여 약간의 여유 허용 (1ms)
        assert elapsed >= delay - 0.001, \
            f"Time between requests ({elapsed:.4f}s) should be >= minimum delay ({delay:.4f}s)"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        delay=delay_strategy
    )
    def test_first_request_does_not_wait(self, domain: str, delay: float):
        """첫 번째 요청은 대기하지 않아야 한다"""
        config = CrawlerConfig(default_delay=delay)
        rate_limiter = RateLimiter(config)
        # Jitter 비활성화하여 정확한 지연 시간 테스트
        rate_limiter.set_jitter_enabled(False)
        
        start_time = time.time()
        wait_time = rate_limiter.wait(domain)
        elapsed = time.time() - start_time
        
        # 첫 번째 요청은 대기 시간이 0이어야 함
        assert wait_time == 0, \
            f"First request should not wait, but waited {wait_time:.4f}s"
        # 실제 경과 시간도 매우 짧아야 함 (10ms 이내)
        assert elapsed < 0.01, \
            f"First request took too long: {elapsed:.4f}s"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        delay=delay_strategy
    )
    def test_wait_returns_actual_wait_time(self, domain: str, delay: float):
        """wait() 메서드는 실제 대기한 시간을 반환해야 한다"""
        config = CrawlerConfig(default_delay=delay)
        rate_limiter = RateLimiter(config)
        # Jitter 비활성화하여 정확한 지연 시간 테스트
        rate_limiter.set_jitter_enabled(False)
        
        # 첫 번째 요청 (대기 없음)
        rate_limiter.wait(domain)
        
        # 두 번째 요청 (대기 필요)
        wait_time = rate_limiter.wait(domain)
        
        # 반환된 대기 시간은 0 이상이어야 함
        assert wait_time >= 0, \
            f"Wait time should be >= 0, got {wait_time}"


class TestExponentialBackoff:
    """
    # **Feature: community-crawler-enhancement, Property 8: Exponential Backoff on Rate Limit**
    
    *For any* 429 응답 후 재시도 시, n번째 재시도의 대기 시간은
    (n-1)번째 재시도의 대기 시간보다 커야 한다 (지수 백오프).
    
    **Validates: Requirements 5.2**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        max_retries=retry_count_strategy
    )
    def test_backoff_delay_increases_exponentially(self, domain: str, max_retries: int):
        """재시도 시 대기 시간이 지수적으로 증가해야 한다"""
        with patch('crawler.utils.rate_limiter.time.sleep'):
            config = CrawlerConfig(max_retries=max_retries)
            rate_limiter = RateLimiter(config)
            
            previous_delay = 0.0
            
            for i in range(max_retries):
                can_retry, delay = rate_limiter.handle_rate_limit(domain)
                
                if can_retry:
                    # 현재 대기 시간은 이전보다 커야 함
                    assert delay > previous_delay, \
                        f"Retry {i+1}: delay ({delay}s) should be > previous ({previous_delay}s)"
                    previous_delay = delay
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy
    )
    def test_backoff_follows_power_of_two(self, domain: str):
        """지수 백오프는 2의 거듭제곱을 따라야 한다"""
        with patch('crawler.utils.rate_limiter.time.sleep'):
            config = CrawlerConfig(max_retries=5)
            rate_limiter = RateLimiter(config)
            
            expected_delays = [2, 4, 8, 16, 32]  # 2^1, 2^2, 2^3, 2^4, 2^5
            
            for i, expected in enumerate(expected_delays):
                can_retry, delay = rate_limiter.handle_rate_limit(domain)
                
                if can_retry:
                    assert delay == expected, \
                        f"Retry {i+1}: expected delay {expected}s, got {delay}s"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        max_retries=retry_count_strategy
    )
    def test_exceeding_max_retries_suspends_domain(self, domain: str, max_retries: int):
        """최대 재시도 횟수 초과 시 도메인이 일시 중단되어야 한다"""
        with patch('crawler.utils.rate_limiter.time.sleep'):
            config = CrawlerConfig(max_retries=max_retries)
            rate_limiter = RateLimiter(config)
            
            # max_retries 횟수만큼 재시도
            for _ in range(max_retries):
                can_retry, _ = rate_limiter.handle_rate_limit(domain)
                assert can_retry, "Should be able to retry within max_retries"
            
            # max_retries + 1 번째 시도
            can_retry, delay = rate_limiter.handle_rate_limit(domain)
            
            assert not can_retry, "Should not be able to retry after exceeding max_retries"
            assert delay == 0.0, "Delay should be 0 when retry is not allowed"
            assert rate_limiter.is_domain_suspended(domain), "Domain should be suspended"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy
    )
    def test_reset_retry_count_clears_counter(self, domain: str):
        """reset_retry_count()는 재시도 카운터를 초기화해야 한다"""
        with patch('crawler.utils.rate_limiter.time.sleep'):
            config = CrawlerConfig(max_retries=3)
            rate_limiter = RateLimiter(config)
            
            # 몇 번 재시도
            rate_limiter.handle_rate_limit(domain)
            rate_limiter.handle_rate_limit(domain)
            
            assert rate_limiter.get_retry_count(domain) == 2
            
            # 카운터 리셋
            rate_limiter.reset_retry_count(domain)
            
            assert rate_limiter.get_retry_count(domain) == 0


class TestDomainSpecificRateLimitSettings:
    """
    # **Feature: community-crawler-enhancement, Property 9: Domain-Specific Rate Limit Settings**
    
    *For any* 도메인별 설정이 적용된 경우, 해당 도메인의 요청은
    개별 설정된 지연 시간을 따라야 한다.
    
    **Validates: Requirements 5.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        custom_delay=delay_strategy,
        default_delay=delay_strategy
    )
    def test_domain_specific_delay_overrides_default(self, domain: str, custom_delay: float, default_delay: float):
        """도메인별 설정은 기본 설정을 오버라이드해야 한다"""
        assume(abs(custom_delay - default_delay) > 0.001)  # 두 값이 다른 경우만 테스트
        
        config = CrawlerConfig(default_delay=default_delay)
        rate_limiter = RateLimiter(config)
        
        # 도메인별 지연 시간 설정
        rate_limiter.set_domain_delay(domain, custom_delay)
        
        # 설정된 지연 시간 확인
        actual_delay = rate_limiter.get_delay_for_domain(domain)
        
        assert actual_delay == custom_delay, \
            f"Domain delay should be {custom_delay}, got {actual_delay}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain_a=domain_strategy,
        domain_b=domain_strategy,
        delay_a=delay_strategy,
        delay_b=delay_strategy
    )
    def test_different_domains_have_independent_settings(self, domain_a: str, domain_b: str, delay_a: float, delay_b: float):
        """서로 다른 도메인은 독립적인 설정을 가져야 한다"""
        assume(domain_a != domain_b)  # 서로 다른 도메인인 경우만 테스트
        
        config = CrawlerConfig(default_delay=0.05)
        rate_limiter = RateLimiter(config)
        
        # 각 도메인에 다른 지연 시간 설정
        rate_limiter.set_domain_delay(domain_a, delay_a)
        rate_limiter.set_domain_delay(domain_b, delay_b)
        
        # 각 도메인의 설정 확인
        assert rate_limiter.get_delay_for_domain(domain_a) == delay_a
        assert rate_limiter.get_delay_for_domain(domain_b) == delay_b
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        default_delay=delay_strategy
    )
    def test_unconfigured_domain_uses_default(self, domain: str, default_delay: float):
        """설정되지 않은 도메인은 기본 지연 시간을 사용해야 한다"""
        config = CrawlerConfig(default_delay=default_delay)
        rate_limiter = RateLimiter(config)
        
        # 도메인별 설정 없이 기본값 확인
        actual_delay = rate_limiter.get_delay_for_domain(domain)
        
        assert actual_delay == default_delay, \
            f"Unconfigured domain should use default delay {default_delay}, got {actual_delay}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        url=url_strategy,
        custom_delay=delay_strategy
    )
    def test_url_extracts_domain_correctly(self, url: str, custom_delay: float):
        """URL에서 도메인을 올바르게 추출해야 한다"""
        config = CrawlerConfig(default_delay=0.05)
        rate_limiter = RateLimiter(config)
        
        # URL로 도메인 설정
        rate_limiter.set_domain_delay(url, custom_delay)
        
        # URL로 조회해도 같은 설정이 반환되어야 함
        assert rate_limiter.get_delay_for_domain(url) == custom_delay
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        domain=domain_strategy,
        custom_delay=delay_strategy
    )
    def test_domain_specific_delay_applied_in_wait(self, domain: str, custom_delay: float):
        """wait() 메서드에서 도메인별 지연 시간이 적용되어야 한다"""
        config = CrawlerConfig(default_delay=0.01)  # 기본값은 작게
        rate_limiter = RateLimiter(config)
        # Jitter 비활성화하여 정확한 지연 시간 테스트
        rate_limiter.set_jitter_enabled(False)
        
        # 도메인별 지연 시간 설정
        rate_limiter.set_domain_delay(domain, custom_delay)
        
        # 첫 번째 요청
        rate_limiter.wait(domain)
        first_time = time.time()
        
        # 두 번째 요청
        rate_limiter.wait(domain)
        second_time = time.time()
        
        elapsed = second_time - first_time
        
        # 도메인별 설정된 지연 시간이 적용되어야 함 (1ms 오차 허용)
        assert elapsed >= custom_delay - 0.001, \
            f"Wait should respect domain-specific delay {custom_delay}, but elapsed {elapsed}"
