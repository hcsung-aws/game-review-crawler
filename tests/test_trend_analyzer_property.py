"""
TrendAnalyzer Property-Based Tests

**Feature: game-analytics-dashboard, Property 11: Sentiment Trend Calculation**
**Validates: Requirements 4.1**

For any 날짜가 있는 게시글 목록에 대해 일별 트렌드를 계산하면,
각 날짜의 감성 평균은 해당 날짜 게시글들의 감성 점수 평균과 일치해야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import uuid
import math

from crawler.models.data_models import PostContent
from crawler.models.analysis_models import TrendPoint, TrendData
from crawler.analysis.trend_analyzer import TrendAnalyzer
from crawler.analysis.sentiment import SentimentAnalyzer


# Strategies for generating test data
@st.composite
def post_with_date_strategy(draw, base_date: datetime = None, days_range: int = 30):
    """날짜가 있는 PostContent 생성 전략"""
    if base_date is None:
        base_date = datetime.now()
    
    # 고유 URL 생성
    url = f"https://example.com/{uuid.uuid4()}"
    
    # 제목과 본문 생성 (감성 분석에 영향을 주는 키워드 포함 가능)
    sentiment_words = draw(st.sampled_from([
        ("좋아요 최고 재미있어요", "positive"),
        ("별로 실망 짜증나요", "negative"),
        ("그냥 보통 평범해요", "neutral"),
        ("", "neutral")
    ]))
    
    title = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    body = sentiment_words[0] + " " + draw(st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    
    site = draw(st.sampled_from(["ruliweb", "inven", "dcinside"]))
    keyword = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    author = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    
    # 날짜 생성 (base_date 기준 days_range 이내)
    days_offset = draw(st.integers(min_value=0, max_value=days_range))
    created_at = base_date - timedelta(days=days_offset)
    # 시간 정보도 추가
    hours = draw(st.integers(min_value=0, max_value=23))
    minutes = draw(st.integers(min_value=0, max_value=59))
    created_at = created_at.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    
    view_count = draw(st.integers(min_value=0, max_value=10000))
    like_count = draw(st.integers(min_value=0, max_value=1000))
    
    return PostContent(
        url=url,
        title=title,
        body=body,
        site=site,
        keyword=keyword,
        author=author,
        created_at=created_at,
        view_count=view_count,
        like_count=like_count,
        comments=[]
    )


@st.composite
def posts_with_dates_strategy(draw, min_posts: int = 1, max_posts: int = 20):
    """날짜가 있는 게시글 목록 생성 전략"""
    base_date = datetime.now()
    num_posts = draw(st.integers(min_value=min_posts, max_value=max_posts))
    
    posts = []
    for _ in range(num_posts):
        post = draw(post_with_date_strategy(base_date=base_date, days_range=30))
        posts.append(post)
    
    return posts


class TestSentimentTrendCalculation:
    """감성 트렌드 계산 Property-Based Tests"""
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_daily_sentiment_average_matches_manual_calculation(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 11: Sentiment Trend Calculation**
        **Validates: Requirements 4.1**
        
        For any 날짜가 있는 게시글 목록에 대해 일별 트렌드를 계산하면,
        각 날짜의 감성 평균은 해당 날짜 게시글들의 감성 점수 평균과 일치해야 한다.
        """
        # 날짜가 있는 게시글만 필터링
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        sentiment_analyzer = SentimentAnalyzer()
        
        # TrendAnalyzer로 트렌드 계산
        trend_data = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="daily")
        
        # 수동으로 날짜별 감성 평균 계산
        date_scores: Dict[str, List[float]] = defaultdict(list)
        for post in posts_with_dates:
            date_key = post.created_at.strftime("%Y-%m-%d")
            sentiment_result = sentiment_analyzer.analyze_post(post)
            date_scores[date_key].append(sentiment_result.score)
        
        # 수동 계산 결과
        manual_averages: Dict[str, float] = {}
        for date_key, scores in date_scores.items():
            manual_averages[date_key] = sum(scores) / len(scores)
        
        # TrendAnalyzer 결과와 수동 계산 결과 비교
        for trend_point in trend_data.data_points:
            date_key = trend_point.date.strftime("%Y-%m-%d")
            
            assert date_key in manual_averages, \
                f"Date {date_key} should exist in manual calculation"
            
            # 부동소수점 비교 (오차 허용)
            assert math.isclose(trend_point.value, manual_averages[date_key], rel_tol=1e-9), \
                f"Trend value {trend_point.value} should match manual average {manual_averages[date_key]} for date {date_key}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_trend_count_matches_post_count_per_date(self, posts):
        """
        각 날짜의 count는 해당 날짜의 게시글 수와 일치해야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="daily")
        
        # 수동으로 날짜별 게시글 수 계산
        date_counts: Dict[str, int] = defaultdict(int)
        for post in posts_with_dates:
            date_key = post.created_at.strftime("%Y-%m-%d")
            date_counts[date_key] += 1
        
        # TrendAnalyzer 결과와 비교
        for trend_point in trend_data.data_points:
            date_key = trend_point.date.strftime("%Y-%m-%d")
            
            assert date_key in date_counts, \
                f"Date {date_key} should exist in manual count"
            
            assert trend_point.count == date_counts[date_key], \
                f"Trend count {trend_point.count} should match manual count {date_counts[date_key]} for date {date_key}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_trend_data_points_are_sorted_by_date(self, posts):
        """
        트렌드 데이터 포인트는 날짜순으로 정렬되어야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="daily")
        
        # 날짜순 정렬 확인
        for i in range(len(trend_data.data_points) - 1):
            assert trend_data.data_points[i].date <= trend_data.data_points[i + 1].date, \
                f"Data points should be sorted by date: {trend_data.data_points[i].date} > {trend_data.data_points[i + 1].date}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_sentiment_score_within_valid_range(self, posts):
        """
        트렌드의 감성 점수는 -1.0 ~ 1.0 범위 내에 있어야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="daily")
        
        for trend_point in trend_data.data_points:
            assert -1.0 <= trend_point.value <= 1.0, \
                f"Sentiment score {trend_point.value} should be within [-1.0, 1.0]"


class TestWeeklyTrendCalculation:
    """주별 트렌드 계산 테스트"""
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_weekly_trend_groups_by_week(self, posts):
        """
        주별 트렌드는 같은 주의 게시글을 그룹화해야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="weekly")
        
        # 주별 트렌드의 날짜는 모두 월요일이어야 함
        for trend_point in trend_data.data_points:
            assert trend_point.date.weekday() == 0, \
                f"Weekly trend date {trend_point.date} should be Monday (weekday=0), got weekday={trend_point.date.weekday()}"


class TestTrendMetadata:
    """트렌드 메타데이터 테스트"""
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_trend_metadata_is_correct(self, posts):
        """
        트렌드 데이터의 메타데이터가 올바르게 설정되어야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # daily 트렌드
        daily_trend = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="daily")
        assert daily_trend.metric_name == "sentiment"
        assert daily_trend.period == "daily"
        
        # weekly 트렌드
        weekly_trend = trend_analyzer.analyze_sentiment_trend(posts_with_dates, period="weekly")
        assert weekly_trend.metric_name == "sentiment"
        assert weekly_trend.period == "weekly"


class TestEmptyAndEdgeCases:
    """빈 데이터 및 엣지 케이스 테스트"""
    
    def test_empty_posts_returns_empty_trend(self):
        """빈 게시글 목록은 빈 트렌드를 반환해야 한다."""
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend([], period="daily")
        
        assert trend_data.metric_name == "sentiment"
        assert trend_data.period == "daily"
        assert len(trend_data.data_points) == 0
    
    def test_posts_without_dates_are_excluded(self):
        """날짜가 없는 게시글은 트렌드 계산에서 제외되어야 한다."""
        posts = [
            PostContent(
                url="https://example.com/1",
                title="Test Post",
                body="Test body",
                site="ruliweb",
                keyword="test",
                created_at=None  # 날짜 없음
            )
        ]
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend(posts, period="daily")
        
        assert len(trend_data.data_points) == 0
    
    def test_single_post_creates_single_data_point(self):
        """단일 게시글은 단일 데이터 포인트를 생성해야 한다."""
        post = PostContent(
            url="https://example.com/1",
            title="Test Post",
            body="좋아요 최고",
            site="ruliweb",
            keyword="test",
            created_at=datetime.now()
        )
        
        trend_analyzer = TrendAnalyzer()
        trend_data = trend_analyzer.analyze_sentiment_trend([post], period="daily")
        
        assert len(trend_data.data_points) == 1
        assert trend_data.data_points[0].count == 1


class TestDateRangeFiltering:
    """기간 필터링 Property-Based Tests
    
    **Feature: game-analytics-dashboard, Property 12: Date Range Filtering**
    **Validates: Requirements 4.3**
    """
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_date_range_filter_returns_only_posts_within_range(self, posts):
        """
        **Feature: game-analytics-dashboard, Property 12: Date Range Filtering**
        **Validates: Requirements 4.3**
        
        For any 시작일과 종료일로 필터링하면,
        결과의 모든 데이터는 해당 기간 내의 날짜를 가져야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # 기간 설정: 15일 전부터 5일 전까지
        base_date = datetime.now()
        start_date = base_date - timedelta(days=15)
        end_date = base_date - timedelta(days=5)
        
        # 기간 필터링 적용하여 트렌드 분석
        trend_data = trend_analyzer.analyze_sentiment_trend(
            posts_with_dates, 
            period="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        # 트렌드 데이터의 모든 날짜는 기간 내에 있어야 함
        start_normalized = datetime(start_date.year, start_date.month, start_date.day)
        end_normalized = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        
        for trend_point in trend_data.data_points:
            assert start_normalized <= trend_point.date <= end_normalized, \
                f"Trend date {trend_point.date} is outside range [{start_normalized}, {end_normalized}]"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_start_date_only_filter(self, posts):
        """
        시작일만 지정하면 시작일 이후의 데이터만 반환해야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # 시작일만 설정: 10일 전부터
        base_date = datetime.now()
        start_date = base_date - timedelta(days=10)
        
        trend_data = trend_analyzer.analyze_sentiment_trend(
            posts_with_dates, 
            period="daily",
            start_date=start_date,
            end_date=None
        )
        
        start_normalized = datetime(start_date.year, start_date.month, start_date.day)
        
        for trend_point in trend_data.data_points:
            assert trend_point.date >= start_normalized, \
                f"Trend date {trend_point.date} should be >= start_date {start_normalized}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_end_date_only_filter(self, posts):
        """
        종료일만 지정하면 종료일 이전의 데이터만 반환해야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # 종료일만 설정: 10일 전까지
        base_date = datetime.now()
        end_date = base_date - timedelta(days=10)
        
        trend_data = trend_analyzer.analyze_sentiment_trend(
            posts_with_dates, 
            period="daily",
            start_date=None,
            end_date=end_date
        )
        
        end_normalized = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        
        for trend_point in trend_data.data_points:
            assert trend_point.date <= end_normalized, \
                f"Trend date {trend_point.date} should be <= end_date {end_normalized}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_no_date_filter_includes_all_posts(self, posts):
        """
        기간 필터가 없으면 모든 게시글이 포함되어야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # 기간 필터 없이 분석
        trend_data = trend_analyzer.analyze_sentiment_trend(
            posts_with_dates, 
            period="daily",
            start_date=None,
            end_date=None
        )
        
        # 총 게시글 수와 트렌드 데이터의 총 count 합이 일치해야 함
        total_count = sum(tp.count for tp in trend_data.data_points)
        assert total_count == len(posts_with_dates), \
            f"Total count {total_count} should equal number of posts {len(posts_with_dates)}"
    
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(posts=posts_with_dates_strategy(min_posts=1, max_posts=10))
    def test_date_filter_excludes_out_of_range_posts(self, posts):
        """
        기간 필터는 범위 밖의 게시글을 제외해야 한다.
        """
        posts_with_dates = [p for p in posts if p.created_at is not None]
        assume(len(posts_with_dates) > 0)
        
        trend_analyzer = TrendAnalyzer()
        
        # 매우 좁은 기간 설정 (1일)
        base_date = datetime.now()
        start_date = base_date - timedelta(days=1)
        end_date = base_date - timedelta(days=1)
        
        trend_data = trend_analyzer.analyze_sentiment_trend(
            posts_with_dates, 
            period="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        # 수동으로 해당 기간의 게시글 수 계산
        start_normalized = datetime(start_date.year, start_date.month, start_date.day)
        end_normalized = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        
        expected_count = sum(
            1 for p in posts_with_dates 
            if start_normalized <= p.created_at <= end_normalized
        )
        
        actual_count = sum(tp.count for tp in trend_data.data_points)
        
        assert actual_count == expected_count, \
            f"Filtered count {actual_count} should equal expected count {expected_count}"


class TestSentimentSpike:
    """감성 급증 탐지 테스트"""
    
    @settings(max_examples=30)
    @given(
        values=st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=15
        )
    )
    def test_spike_detection_returns_only_below_threshold(self, values):
        """
        감성 급증 탐지는 threshold 미만의 값만 반환해야 한다.
        """
        trend_analyzer = TrendAnalyzer()
        
        # TrendData 생성
        data_points = []
        base_date = datetime.now()
        for i, value in enumerate(values):
            data_points.append(TrendPoint(
                date=base_date - timedelta(days=i),
                value=value,
                count=1
            ))
        
        trend_data = TrendData(
            metric_name="sentiment",
            period="daily",
            data_points=data_points
        )
        
        threshold = -0.3
        spikes = trend_analyzer.detect_sentiment_spike(trend_data, threshold=threshold)
        
        # 모든 spike는 threshold 미만이어야 함
        for spike in spikes:
            assert spike.value < threshold, \
                f"Spike value {spike.value} should be below threshold {threshold}"
        
        # threshold 미만인 모든 값이 spike에 포함되어야 함
        expected_spike_count = sum(1 for v in values if v < threshold)
        assert len(spikes) == expected_spike_count, \
            f"Expected {expected_spike_count} spikes, got {len(spikes)}"
