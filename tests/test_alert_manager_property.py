"""
Property-Based Tests for Alert Manager

**Feature: game-analytics-dashboard, Property 19: Urgent Alert Classification**
**Validates: Requirements 8.4**

For any 이슈에 대해 24시간 내 관련 게시글이 10개 이상이면 
긴급 알림으로 분류되어야 한다.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime, timedelta
from typing import List

from crawler.analysis.alert_manager import (
    AlertManager, 
    Alert, 
    AlertType, 
    AlertPriority
)
from crawler.models.analysis_models import (
    KeywordCluster, 
    DetectedIssue, 
    IssueSeverity,
    TrendPoint
)
from crawler.models.data_models import PostContent, Comment


# Custom strategies for generating test data
@st.composite
def post_content_strategy(draw, created_at: datetime = None):
    """PostContent 객체 생성 전략"""
    keywords = ["업데이트", "버그", "오류", "패치", "이벤트", "보상", "밸런스", "캐릭터"]
    
    title_words = draw(st.lists(
        st.sampled_from(keywords),
        min_size=1,
        max_size=5
    ))
    body_words = draw(st.lists(
        st.sampled_from(keywords),
        min_size=1,
        max_size=20
    ))
    
    if created_at is None:
        # 최근 48시간 내 랜덤 시간
        hours_ago = draw(st.integers(min_value=0, max_value=48))
        created_at = datetime.now() - timedelta(hours=hours_ago)
    
    post_id = draw(st.integers(min_value=1, max_value=100000))
    
    return PostContent(
        url=f"https://example.com/post/{post_id}",
        title=" ".join(title_words),
        body=" ".join(body_words),
        site="test_site",
        keyword="test_keyword",
        author="test_author",
        created_at=created_at,
        view_count=draw(st.integers(min_value=0, max_value=100000)),
        like_count=draw(st.integers(min_value=0, max_value=10000)),
        comments=[]
    )


@st.composite
def recent_post_strategy(draw):
    """최근 24시간 내 게시글 생성 전략"""
    hours_ago = draw(st.integers(min_value=0, max_value=23))
    created_at = datetime.now() - timedelta(hours=hours_ago)
    return draw(post_content_strategy(created_at=created_at))


@st.composite
def old_post_strategy(draw):
    """24시간 이전 게시글 생성 전략"""
    hours_ago = draw(st.integers(min_value=25, max_value=72))
    created_at = datetime.now() - timedelta(hours=hours_ago)
    return draw(post_content_strategy(created_at=created_at))


@st.composite
def keyword_cluster_strategy(draw):
    """KeywordCluster 객체 생성 전략"""
    keywords = draw(st.lists(
        st.text(min_size=2, max_size=10, alphabet="가나다라마바사아자차카타파하"),
        min_size=1,
        max_size=5,
        unique=True
    ))
    assume(len(keywords) >= 1)
    
    return KeywordCluster(
        cluster_id=f"cluster_{draw(st.integers(min_value=1, max_value=1000))}",
        keywords=keywords,
        representative=keywords[0],
        post_count=draw(st.integers(min_value=0, max_value=100)),
        total_views=draw(st.integers(min_value=0, max_value=100000)),
        total_comments=draw(st.integers(min_value=0, max_value=1000))
    )


@st.composite
def detected_issue_with_posts_strategy(draw, post_urls: List[str]):
    """관련 게시글 URL이 있는 DetectedIssue 생성 전략"""
    cluster = draw(keyword_cluster_strategy())
    
    return DetectedIssue(
        issue_id=f"issue_{draw(st.integers(min_value=1, max_value=10000))}",
        title=cluster.representative,
        cluster=cluster,
        priority_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        is_hot=False,
        is_bug=draw(st.booleans()),
        severity=draw(st.sampled_from(list(IssueSeverity))),
        related_posts=post_urls,
        first_seen=datetime.now(),
        sentiment_avg=draw(st.floats(min_value=-1.0, max_value=1.0))
    )


class TestUrgentAlertClassification:
    """
    **Feature: game-analytics-dashboard, Property 19: Urgent Alert Classification**
    **Validates: Requirements 8.4**
    
    For any 이슈에 대해 24시간 내 관련 게시글이 10개 이상이면 
    긴급 알림으로 분류되어야 한다.
    """
    
    @given(
        num_recent_posts=st.integers(min_value=10, max_value=30),
        num_old_posts=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_urgent_alert_when_10_or_more_recent_posts(
        self, 
        num_recent_posts: int, 
        num_old_posts: int
    ):
        """24시간 내 10개 이상 게시글이 있으면 긴급 알림으로 분류되는지 검증"""
        manager = AlertManager()
        
        # 최근 24시간 내 게시글 생성
        recent_posts = []
        for i in range(num_recent_posts):
            hours_ago = i % 24  # 0~23시간 전
            created_at = datetime.now() - timedelta(hours=hours_ago)
            post = PostContent(
                url=f"https://example.com/recent/{i}",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다",
                site="test_site",
                keyword="test",
                created_at=created_at,
                view_count=100
            )
            recent_posts.append(post)
        
        # 24시간 이전 게시글 생성
        old_posts = []
        for i in range(num_old_posts):
            hours_ago = 25 + i  # 25시간 이상 전
            created_at = datetime.now() - timedelta(hours=hours_ago)
            post = PostContent(
                url=f"https://example.com/old/{i}",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다",
                site="test_site",
                keyword="test",
                created_at=created_at,
                view_count=100
            )
            old_posts.append(post)
        
        all_posts = recent_posts + old_posts
        all_urls = [p.url for p in all_posts]
        
        # 이슈 생성 (모든 게시글을 관련 게시글로 설정)
        issue = DetectedIssue(
            issue_id="issue_1",
            title="버그",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["버그"],
                representative="버그",
                post_count=len(all_posts)
            ),
            priority_score=0.8,
            related_posts=all_urls
        )
        
        # 긴급 알림 분류 확인
        is_urgent = manager.classify_urgent_alert(
            posts=all_posts,
            issue=issue,
            hours=24,
            min_posts=10
        )
        
        assert is_urgent is True, \
            f"Should be urgent with {num_recent_posts} recent posts (>= 10)"
    
    @given(
        num_recent_posts=st.integers(min_value=0, max_value=9),
        num_old_posts=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_not_urgent_when_less_than_10_recent_posts(
        self, 
        num_recent_posts: int, 
        num_old_posts: int
    ):
        """24시간 내 10개 미만 게시글이면 긴급 알림이 아닌지 검증"""
        manager = AlertManager()
        
        # 최근 24시간 내 게시글 생성
        recent_posts = []
        for i in range(num_recent_posts):
            hours_ago = i % 24
            created_at = datetime.now() - timedelta(hours=hours_ago)
            post = PostContent(
                url=f"https://example.com/recent/{i}",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다",
                site="test_site",
                keyword="test",
                created_at=created_at,
                view_count=100
            )
            recent_posts.append(post)
        
        # 24시간 이전 게시글 생성
        old_posts = []
        for i in range(num_old_posts):
            hours_ago = 25 + i
            created_at = datetime.now() - timedelta(hours=hours_ago)
            post = PostContent(
                url=f"https://example.com/old/{i}",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다",
                site="test_site",
                keyword="test",
                created_at=created_at,
                view_count=100
            )
            old_posts.append(post)
        
        all_posts = recent_posts + old_posts
        all_urls = [p.url for p in all_posts]
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="버그",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["버그"],
                representative="버그",
                post_count=len(all_posts)
            ),
            priority_score=0.8,
            related_posts=all_urls
        )
        
        is_urgent = manager.classify_urgent_alert(
            posts=all_posts,
            issue=issue,
            hours=24,
            min_posts=10
        )
        
        assert is_urgent is False, \
            f"Should NOT be urgent with {num_recent_posts} recent posts (< 10)"
    
    @given(
        hours=st.integers(min_value=1, max_value=72),
        min_posts=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_urgent_classification_respects_parameters(
        self, 
        hours: int, 
        min_posts: int
    ):
        """긴급 알림 분류가 파라미터를 올바르게 적용하는지 검증"""
        manager = AlertManager()
        
        # 정확히 min_posts 개의 게시글을 hours 시간 내에 생성
        posts = []
        for i in range(min_posts):
            hours_ago = i % hours if hours > 0 else 0
            created_at = datetime.now() - timedelta(hours=hours_ago)
            post = PostContent(
                url=f"https://example.com/post/{i}",
                title="테스트",
                body="테스트 본문",
                site="test_site",
                keyword="test",
                created_at=created_at,
                view_count=100
            )
            posts.append(post)
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="테스트",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["테스트"],
                representative="테스트",
                post_count=len(posts)
            ),
            priority_score=0.5,
            related_posts=[p.url for p in posts]
        )
        
        is_urgent = manager.classify_urgent_alert(
            posts=posts,
            issue=issue,
            hours=hours,
            min_posts=min_posts
        )
        
        # 정확히 min_posts 개이므로 긴급 알림이어야 함
        assert is_urgent is True, \
            f"Should be urgent with exactly {min_posts} posts in {hours} hours"
    
    def test_empty_posts_not_urgent(self):
        """빈 게시글 목록은 긴급 알림이 아닌지 검증"""
        manager = AlertManager()
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="테스트",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["테스트"],
                representative="테스트"
            ),
            priority_score=0.5,
            related_posts=[]
        )
        
        is_urgent = manager.classify_urgent_alert(
            posts=[],
            issue=issue
        )
        
        assert is_urgent is False
    
    def test_issue_without_related_posts_not_urgent(self):
        """관련 게시글이 없는 이슈는 긴급 알림이 아닌지 검증"""
        manager = AlertManager()
        
        posts = [
            PostContent(
                url=f"https://example.com/post/{i}",
                title="테스트",
                body="테스트",
                site="test",
                keyword="test",
                created_at=datetime.now(),
                view_count=100
            )
            for i in range(20)
        ]
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="테스트",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["테스트"],
                representative="테스트"
            ),
            priority_score=0.5,
            related_posts=[]  # 관련 게시글 없음
        )
        
        is_urgent = manager.classify_urgent_alert(
            posts=posts,
            issue=issue
        )
        
        assert is_urgent is False
    
    def test_count_posts_in_period_accuracy(self):
        """기간 내 게시글 수 계산이 정확한지 검증"""
        manager = AlertManager()
        
        # 12시간 전 게시글 5개
        recent_posts = [
            PostContent(
                url=f"https://example.com/recent/{i}",
                title="테스트",
                body="테스트",
                site="test",
                keyword="test",
                created_at=datetime.now() - timedelta(hours=12),
                view_count=100
            )
            for i in range(5)
        ]
        
        # 36시간 전 게시글 5개
        old_posts = [
            PostContent(
                url=f"https://example.com/old/{i}",
                title="테스트",
                body="테스트",
                site="test",
                keyword="test",
                created_at=datetime.now() - timedelta(hours=36),
                view_count=100
            )
            for i in range(5)
        ]
        
        all_posts = recent_posts + old_posts
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="테스트",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["테스트"],
                representative="테스트"
            ),
            priority_score=0.5,
            related_posts=[p.url for p in all_posts]
        )
        
        count = manager.count_posts_in_period(
            posts=all_posts,
            issue=issue,
            hours=24
        )
        
        assert count == 5, f"Expected 5 recent posts, got {count}"
    
    @given(num_posts=st.integers(min_value=10, max_value=30))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_urgent_alert_has_correct_properties(self, num_posts: int):
        """긴급 알림이 올바른 속성을 가지는지 검증"""
        manager = AlertManager()
        
        posts = [
            PostContent(
                url=f"https://example.com/post/{i}",
                title="버그 발생",
                body="게임에서 버그가 발생했습니다",
                site="test_site",
                keyword="test",
                created_at=datetime.now() - timedelta(hours=i % 24),
                view_count=100
            )
            for i in range(num_posts)
        ]
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="버그",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["버그"],
                representative="버그",
                post_count=num_posts
            ),
            priority_score=0.8,
            related_posts=[p.url for p in posts]
        )
        
        alert = manager.create_urgent_alert(
            issue=issue,
            game_id="test_game",
            post_count_in_period=num_posts
        )
        
        # 긴급 알림 속성 검증
        assert alert.is_urgent is True
        assert alert.alert_type == AlertType.URGENT
        assert alert.priority == AlertPriority.CRITICAL
        assert alert.game_id == "test_game"
        assert alert.related_issue_id == issue.issue_id
        assert "긴급" in alert.title
        assert str(num_posts) in alert.message



class TestHotIssueAlert:
    """Hot Issue 알림 생성 테스트"""
    
    def test_hot_issue_alert_creation(self):
        """Hot Issue 알림이 올바르게 생성되는지 검증"""
        manager = AlertManager()
        
        issue = DetectedIssue(
            issue_id="issue_1",
            title="업데이트 문제",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["업데이트", "패치"],
                representative="업데이트",
                post_count=50,
                total_views=10000,
                total_comments=200
            ),
            priority_score=0.9,
            is_hot=True,
            related_posts=["https://example.com/1", "https://example.com/2"]
        )
        
        alert = manager.create_hot_issue_alert(issue, "test_game")
        
        assert alert.alert_type == AlertType.HOT_ISSUE
        assert alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]
        assert "Hot Issue" in alert.title
        assert issue.title in alert.title
        assert alert.game_id == "test_game"
        assert alert.related_issue_id == issue.issue_id
    
    def test_bug_hot_issue_has_higher_priority(self):
        """버그 관련 Hot Issue가 더 높은 우선순위를 가지는지 검증"""
        manager = AlertManager()
        
        bug_issue = DetectedIssue(
            issue_id="bug_issue",
            title="버그",
            cluster=KeywordCluster(
                cluster_id="cluster_1",
                keywords=["버그"],
                representative="버그",
                post_count=50
            ),
            priority_score=0.9,
            is_hot=True,
            is_bug=True,
            severity=IssueSeverity.CRITICAL
        )
        
        alert = manager.create_hot_issue_alert(bug_issue, "test_game")
        
        assert alert.priority == AlertPriority.CRITICAL


class TestSentimentSpikeAlert:
    """부정적 감성 급증 알림 테스트"""
    
    def test_sentiment_spike_alert_creation(self):
        """부정적 감성 급증 알림이 올바르게 생성되는지 검증"""
        manager = AlertManager()
        
        spike_point = TrendPoint(
            date=datetime.now(),
            value=-0.5,
            count=20
        )
        
        alert = manager.create_sentiment_spike_alert(
            spike_point=spike_point,
            game_id="test_game",
            related_posts=["https://example.com/1"]
        )
        
        assert alert.alert_type == AlertType.SENTIMENT_SPIKE
        assert "부정적 감성" in alert.title
        assert alert.game_id == "test_game"
    
    @given(sentiment_value=st.floats(min_value=-1.0, max_value=-0.3))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_sentiment_spike_priority_based_on_severity(self, sentiment_value: float):
        """감성 급증 심각도에 따른 우선순위 검증"""
        manager = AlertManager()
        
        spike_point = TrendPoint(
            date=datetime.now(),
            value=sentiment_value,
            count=10
        )
        
        alert = manager.create_sentiment_spike_alert(
            spike_point=spike_point,
            game_id="test_game"
        )
        
        # 심각도에 따른 우선순위 검증
        if sentiment_value < -0.6:
            assert alert.priority == AlertPriority.CRITICAL
        elif sentiment_value < -0.4:
            assert alert.priority == AlertPriority.HIGH
        else:
            assert alert.priority == AlertPriority.MEDIUM


class TestAlertSummary:
    """알림 요약 테스트"""
    
    def test_empty_alerts_summary(self):
        """빈 알림 목록의 요약 검증"""
        manager = AlertManager()
        
        summary = manager.get_alerts_summary([])
        
        assert summary["total_alerts"] == 0
        assert summary["urgent_count"] == 0
        assert summary["hot_issue_count"] == 0
        assert summary["sentiment_spike_count"] == 0
        assert summary["top_alert"] is None
    
    def test_alerts_summary_counts(self):
        """알림 요약의 카운트가 정확한지 검증"""
        manager = AlertManager()
        
        alerts = [
            Alert(
                alert_id="1",
                alert_type=AlertType.HOT_ISSUE,
                priority=AlertPriority.HIGH,
                title="Hot Issue 1",
                message="Test",
                created_at=datetime.now(),
                game_id="test",
                is_urgent=False
            ),
            Alert(
                alert_id="2",
                alert_type=AlertType.URGENT,
                priority=AlertPriority.CRITICAL,
                title="Urgent 1",
                message="Test",
                created_at=datetime.now(),
                game_id="test",
                is_urgent=True
            ),
            Alert(
                alert_id="3",
                alert_type=AlertType.SENTIMENT_SPIKE,
                priority=AlertPriority.MEDIUM,
                title="Spike 1",
                message="Test",
                created_at=datetime.now(),
                game_id="test",
                is_urgent=False
            )
        ]
        
        summary = manager.get_alerts_summary(alerts)
        
        assert summary["total_alerts"] == 3
        assert summary["urgent_count"] == 1
        assert summary["hot_issue_count"] == 1
        assert summary["sentiment_spike_count"] == 1
        assert summary["critical_count"] == 1
        assert summary["top_alert"] is not None
