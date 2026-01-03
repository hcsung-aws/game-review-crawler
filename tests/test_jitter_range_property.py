"""
Jitter Range Compliance Property-Based Tests

Property-based testing using Hypothesis library.
Each test runs minimum 100 iterations.

# **Feature: community-crawler-enhancement, Property 13: Jitter Range Compliance**

*For any* 요청에 적용되는 랜덤 지연은 설정된 jitter_range 범위 내에 있어야 한다.

**Validates: Requirements 8.1, 8.2**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from crawler.utils.rate_limiter import RateLimiter
from crawler.models.data_models import CrawlerConfig


# Jitter 범위 전략 (min <= max 보장)
@st.composite
def jitter_range_strategy(draw):
    """유효한 jitter 범위 생성 (min <= max, 둘 다 0 이상)"""
    jitter_min = draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    jitter_max = draw(st.floats(min_value=jitter_min, max_value=10.0, allow_nan=False, allow_infinity=False))
    return (jitter_min, jitter_max)


# 기본 지연 시간 전략
base_delay_strategy = st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)


class TestJitterRangeCompliance:
    """
    # **Feature: community-crawler-enhancement, Property 13: Jitter Range Compliance**
    
    *For any* 요청에 적용되는 랜덤 지연은 설정된 jitter_range 범위 내에 있어야 한다.
    
    **Validates: Requirements 8.1, 8.2**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        base_delay=base_delay_strategy,
        jitter_range=jitter_range_strategy()
    )
    def test_jitter_within_configured_range(self, base_delay: float, jitter_range: tuple):
        """_add_jitter()가 반환하는 값은 base_delay + jitter_min 이상, base_delay + jitter_max 이하여야 한다"""
        jitter_min, jitter_max = jitter_range
        
        config = CrawlerConfig(
            default_delay=base_delay,
            jitter_range=jitter_range
        )
        rate_limiter = RateLimiter(config)
        
        # _add_jitter 메서드 호출
        result = rate_limiter._add_jitter(base_delay)
        
        expected_min = base_delay + jitter_min
        expected_max = base_delay + jitter_max
        
        assert result >= expected_min, \
            f"Jitter result ({result}) should be >= base_delay + jitter_min ({expected_min})"
        assert result <= expected_max, \
            f"Jitter result ({result}) should be <= base_delay + jitter_max ({expected_max})"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        jitter_range=jitter_range_strategy()
    )
    def test_set_jitter_range_updates_correctly(self, jitter_range: tuple):
        """set_jitter_range()로 설정한 범위가 올바르게 적용되어야 한다"""
        jitter_min, jitter_max = jitter_range
        
        rate_limiter = RateLimiter()
        rate_limiter.set_jitter_range(jitter_min, jitter_max)
        
        actual_range = rate_limiter.get_jitter_range()
        
        assert actual_range == jitter_range, \
            f"Jitter range should be {jitter_range}, got {actual_range}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        base_delay=base_delay_strategy,
        jitter_range=jitter_range_strategy()
    )
    def test_multiple_jitter_calls_all_within_range(self, base_delay: float, jitter_range: tuple):
        """여러 번 _add_jitter()를 호출해도 모두 범위 내에 있어야 한다"""
        jitter_min, jitter_max = jitter_range
        
        config = CrawlerConfig(
            default_delay=base_delay,
            jitter_range=jitter_range
        )
        rate_limiter = RateLimiter(config)
        
        expected_min = base_delay + jitter_min
        expected_max = base_delay + jitter_max
        
        # 여러 번 호출하여 모두 범위 내인지 확인
        for i in range(10):
            result = rate_limiter._add_jitter(base_delay)
            
            assert result >= expected_min, \
                f"Call {i+1}: Jitter result ({result}) should be >= {expected_min}"
            assert result <= expected_max, \
                f"Call {i+1}: Jitter result ({result}) should be <= {expected_max}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        jitter_min=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        jitter_max=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)
    )
    def test_invalid_jitter_range_raises_error(self, jitter_min: float, jitter_max: float):
        """jitter_min > jitter_max인 경우 ValueError가 발생해야 한다"""
        assume(jitter_min > jitter_max)  # min이 max보다 큰 경우만 테스트
        
        rate_limiter = RateLimiter()
        
        with pytest.raises(ValueError):
            rate_limiter.set_jitter_range(jitter_min, jitter_max)
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        negative_min=st.floats(min_value=-10.0, max_value=-0.001, allow_nan=False, allow_infinity=False)
    )
    def test_negative_jitter_min_raises_error(self, negative_min: float):
        """음수 jitter_min은 ValueError가 발생해야 한다"""
        rate_limiter = RateLimiter()
        
        with pytest.raises(ValueError):
            rate_limiter.set_jitter_range(negative_min, 1.0)
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        base_delay=base_delay_strategy
    )
    def test_zero_jitter_range_returns_base_delay(self, base_delay: float):
        """jitter_min == jitter_max == 0인 경우 base_delay만 반환해야 한다"""
        config = CrawlerConfig(
            default_delay=base_delay,
            jitter_range=(0.0, 0.0)
        )
        rate_limiter = RateLimiter(config)
        
        result = rate_limiter._add_jitter(base_delay)
        
        assert result == base_delay, \
            f"With zero jitter range, result ({result}) should equal base_delay ({base_delay})"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        jitter_value=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        base_delay=base_delay_strategy
    )
    def test_equal_jitter_min_max_returns_deterministic_value(self, jitter_value: float, base_delay: float):
        """jitter_min == jitter_max인 경우 항상 동일한 값을 반환해야 한다"""
        config = CrawlerConfig(
            default_delay=base_delay,
            jitter_range=(jitter_value, jitter_value)
        )
        rate_limiter = RateLimiter(config)
        
        expected = base_delay + jitter_value
        
        # 여러 번 호출해도 동일한 값
        for _ in range(5):
            result = rate_limiter._add_jitter(base_delay)
            assert result == expected, \
                f"With equal jitter min/max, result ({result}) should equal {expected}"
