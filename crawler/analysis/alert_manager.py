"""
알림 관리 모듈

Requirements: 8.1, 8.2, 8.3, 8.4
- Hot Issue 알림 생성
- 부정적 감성 급증 알림 생성
- 긴급 알림 분류 (24시간 내 10개 이상)
- 알림 요약 및 관련 게시글 링크 포함
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

from crawler.models.data_models import PostContent
from crawler.models.analysis_models import (
    DetectedIssue,
    TrendData,
    TrendPoint,
    SentimentResult,
    IssueSeverity
)
from crawler.analysis.sentiment import SentimentAnalyzer
from crawler.analysis.issue_detector import IssueDetector
from crawler.analysis.trend_analyzer import TrendAnalyzer


class AlertType(Enum):
    """알림 유형"""
    HOT_ISSUE = "hot_issue"
    SENTIMENT_SPIKE = "sentiment_spike"
    URGENT = "urgent"
    BUG_CRITICAL = "bug_critical"


class AlertPriority(Enum):
    """알림 우선순위"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Alert:
    """알림 데이터 모델
    
    Requirements: 8.1, 8.2, 8.3
    - 이슈 요약과 관련 게시글 링크 포함
    """
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str
    created_at: datetime
    game_id: str
    related_posts: List[str] = field(default_factory=list)
    related_issue_id: Optional[str] = None
    is_urgent: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "game_id": self.game_id,
            "related_posts": self.related_posts,
            "related_issue_id": self.related_issue_id,
            "is_urgent": self.is_urgent,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """딕셔너리에서 객체 생성"""
        return cls(
            alert_id=data["alert_id"],
            alert_type=AlertType(data["alert_type"]),
            priority=AlertPriority(data["priority"]),
            title=data["title"],
            message=data["message"],
            created_at=datetime.fromisoformat(data["created_at"]),
            game_id=data["game_id"],
            related_posts=data.get("related_posts", []),
            related_issue_id=data.get("related_issue_id"),
            is_urgent=data.get("is_urgent", False),
            metadata=data.get("metadata", {})
        )


class AlertManager:
    """알림 관리자
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    - Hot Issue 알림 생성
    - 부정적 감성 급증 알림 생성
    - 긴급 알림 분류 (24시간 내 10개 이상)
    """
    
    # 긴급 알림 기준
    URGENT_HOURS = 24
    URGENT_MIN_POSTS = 10
    
    # 부정적 감성 급증 임계값
    SENTIMENT_SPIKE_THRESHOLD = -0.3
    
    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        issue_detector: Optional[IssueDetector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None
    ):
        """알림 관리자 초기화
        
        Args:
            sentiment_analyzer: 감성 분석기
            issue_detector: 이슈 탐지기
            trend_analyzer: 트렌드 분석기
        """
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.issue_detector = issue_detector or IssueDetector(self.sentiment_analyzer)
        self.trend_analyzer = trend_analyzer or TrendAnalyzer(self.sentiment_analyzer)
        self._alerts: List[Alert] = []
    
    def _generate_alert_id(self) -> str:
        """알림 ID 생성"""
        return f"alert_{uuid.uuid4().hex[:8]}"
    
    def create_hot_issue_alert(
        self,
        issue: DetectedIssue,
        game_id: str
    ) -> Alert:
        """Hot Issue 알림 생성
        
        Requirements: 8.1
        - Hot_Issue가 새로 탐지되면 대시보드 상단에 알림 표시
        
        Args:
            issue: 탐지된 Hot Issue
            game_id: 게임 ID
            
        Returns:
            생성된 Alert 객체
        """
        # 우선순위 결정
        priority = AlertPriority.HIGH
        if issue.is_bug and issue.severity == IssueSeverity.CRITICAL:
            priority = AlertPriority.CRITICAL
        
        # 메시지 생성
        message = f"'{issue.title}' 이슈가 급부상하고 있습니다. "
        message += f"관련 게시글 {issue.cluster.post_count}개, "
        message += f"총 조회수 {issue.cluster.total_views:,}회"
        
        if issue.is_bug:
            message += f" (버그 관련, 심각도: {issue.severity.value})"
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.HOT_ISSUE,
            priority=priority,
            title=f"🔥 Hot Issue: {issue.title}",
            message=message,
            created_at=datetime.now(),
            game_id=game_id,
            related_posts=issue.related_posts[:10],  # 최대 10개
            related_issue_id=issue.issue_id,
            is_urgent=False,
            metadata={
                "post_count": issue.cluster.post_count,
                "total_views": issue.cluster.total_views,
                "priority_score": issue.priority_score,
                "sentiment_avg": issue.sentiment_avg
            }
        )
        
        return alert
    
    def create_sentiment_spike_alert(
        self,
        spike_point: TrendPoint,
        game_id: str,
        related_posts: Optional[List[str]] = None
    ) -> Alert:
        """부정적 감성 급증 알림 생성
        
        Requirements: 8.2
        - 부정적 감성 급증이 탐지되면 경고 알림 표시
        
        Args:
            spike_point: 감성 급증 데이터 포인트
            game_id: 게임 ID
            related_posts: 관련 게시글 URL 목록
            
        Returns:
            생성된 Alert 객체
        """
        # 심각도에 따른 우선순위
        if spike_point.value < -0.6:
            priority = AlertPriority.CRITICAL
        elif spike_point.value < -0.4:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM
        
        date_str = spike_point.date.strftime("%Y-%m-%d")
        message = f"{date_str}에 부정적 감성이 급증했습니다. "
        message += f"평균 감성 점수: {spike_point.value:.2f}, "
        message += f"관련 게시글 {spike_point.count}개"
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.SENTIMENT_SPIKE,
            priority=priority,
            title=f"⚠️ 부정적 감성 급증 ({date_str})",
            message=message,
            created_at=datetime.now(),
            game_id=game_id,
            related_posts=related_posts or [],
            is_urgent=False,
            metadata={
                "spike_date": date_str,
                "sentiment_value": spike_point.value,
                "post_count": spike_point.count
            }
        )
        
        return alert
    
    def create_urgent_alert(
        self,
        issue: DetectedIssue,
        game_id: str,
        post_count_in_period: int
    ) -> Alert:
        """긴급 알림 생성
        
        Requirements: 8.4
        - 24시간 내 동일 이슈에 대한 게시글이 10개 이상이면 긴급 알림
        
        Args:
            issue: 탐지된 이슈
            game_id: 게임 ID
            post_count_in_period: 기간 내 게시글 수
            
        Returns:
            생성된 Alert 객체
        """
        message = f"'{issue.title}' 이슈가 긴급 상황입니다! "
        message += f"최근 {self.URGENT_HOURS}시간 내 {post_count_in_period}개의 게시글이 작성되었습니다."
        
        if issue.is_bug:
            message += f" (버그 관련, 심각도: {issue.severity.value})"
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            alert_type=AlertType.URGENT,
            priority=AlertPriority.CRITICAL,
            title=f"🚨 긴급: {issue.title}",
            message=message,
            created_at=datetime.now(),
            game_id=game_id,
            related_posts=issue.related_posts[:10],
            related_issue_id=issue.issue_id,
            is_urgent=True,
            metadata={
                "post_count_in_period": post_count_in_period,
                "hours": self.URGENT_HOURS,
                "priority_score": issue.priority_score,
                "is_bug": issue.is_bug
            }
        )
        
        return alert

    
    def classify_urgent_alert(
        self,
        posts: List[PostContent],
        issue: DetectedIssue,
        hours: int = 24,
        min_posts: int = 10
    ) -> bool:
        """긴급 알림 여부 분류
        
        Requirements: 8.4
        - 24시간 내 동일 이슈에 대한 게시글이 10개 이상이면 긴급 알림으로 분류
        
        Args:
            posts: 게시글 목록
            issue: 탐지된 이슈
            hours: 시간 범위 (기본값: 24시간)
            min_posts: 최소 게시글 수 (기본값: 10개)
            
        Returns:
            긴급 알림 여부
        """
        if not posts or not issue.related_posts:
            return False
        
        # 현재 시간 기준 N시간 전
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        
        # 이슈 관련 게시글 중 기간 내 게시글 수 계산
        related_post_urls = set(issue.related_posts)
        recent_count = 0
        
        for post in posts:
            if post.url in related_post_urls:
                if post.created_at and post.created_at >= cutoff_time:
                    recent_count += 1
        
        return recent_count >= min_posts
    
    def count_posts_in_period(
        self,
        posts: List[PostContent],
        issue: DetectedIssue,
        hours: int = 24
    ) -> int:
        """기간 내 이슈 관련 게시글 수 계산
        
        Args:
            posts: 게시글 목록
            issue: 탐지된 이슈
            hours: 시간 범위
            
        Returns:
            기간 내 게시글 수
        """
        if not posts or not issue.related_posts:
            return 0
        
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        
        related_post_urls = set(issue.related_posts)
        count = 0
        
        for post in posts:
            if post.url in related_post_urls:
                if post.created_at and post.created_at >= cutoff_time:
                    count += 1
        
        return count
    
    def generate_alerts(
        self,
        posts: List[PostContent],
        game_id: str,
        include_hot_issues: bool = True,
        include_sentiment_spikes: bool = True,
        include_urgent: bool = True
    ) -> List[Alert]:
        """게시글 목록에서 알림 생성
        
        Requirements: 8.1, 8.2, 8.3, 8.4
        - Hot Issue 알림
        - 부정적 감성 급증 알림
        - 긴급 알림
        
        Args:
            posts: 게시글 목록
            game_id: 게임 ID
            include_hot_issues: Hot Issue 알림 포함 여부
            include_sentiment_spikes: 감성 급증 알림 포함 여부
            include_urgent: 긴급 알림 포함 여부
            
        Returns:
            생성된 Alert 목록
        """
        alerts = []
        
        if not posts:
            return alerts
        
        # 이슈 탐지
        issues = self.issue_detector.detect_issues(posts)
        hot_issues = self.issue_detector.detect_hot_issues(issues)
        
        # Hot Issue 알림 생성
        if include_hot_issues:
            for issue in hot_issues:
                alert = self.create_hot_issue_alert(issue, game_id)
                alerts.append(alert)
        
        # 긴급 알림 확인 및 생성
        if include_urgent:
            for issue in issues:
                if self.classify_urgent_alert(posts, issue):
                    post_count = self.count_posts_in_period(posts, issue)
                    alert = self.create_urgent_alert(issue, game_id, post_count)
                    alerts.append(alert)
        
        # 감성 트렌드 분석 및 급증 알림
        if include_sentiment_spikes:
            trend = self.trend_analyzer.analyze_sentiment_trend(posts, period="daily")
            spikes = self.trend_analyzer.detect_sentiment_spike(
                trend, 
                threshold=self.SENTIMENT_SPIKE_THRESHOLD
            )
            
            for spike in spikes:
                # 해당 날짜의 관련 게시글 찾기
                spike_date = spike.date.date()
                related_posts = [
                    p.url for p in posts 
                    if p.created_at and p.created_at.date() == spike_date
                ]
                
                alert = self.create_sentiment_spike_alert(
                    spike, game_id, related_posts[:10]
                )
                alerts.append(alert)
        
        # 우선순위 순으로 정렬
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3
        }
        alerts.sort(key=lambda x: (priority_order.get(x.priority, 4), x.created_at), reverse=False)
        
        self._alerts = alerts
        return alerts
    
    def get_urgent_alerts(self, alerts: Optional[List[Alert]] = None) -> List[Alert]:
        """긴급 알림만 필터링
        
        Args:
            alerts: 알림 목록 (None이면 내부 저장된 알림 사용)
            
        Returns:
            긴급 알림 목록
        """
        target_alerts = alerts if alerts is not None else self._alerts
        return [a for a in target_alerts if a.is_urgent]
    
    def get_alerts_by_type(
        self, 
        alert_type: AlertType,
        alerts: Optional[List[Alert]] = None
    ) -> List[Alert]:
        """유형별 알림 필터링
        
        Args:
            alert_type: 알림 유형
            alerts: 알림 목록 (None이면 내부 저장된 알림 사용)
            
        Returns:
            해당 유형의 알림 목록
        """
        target_alerts = alerts if alerts is not None else self._alerts
        return [a for a in target_alerts if a.alert_type == alert_type]
    
    def get_alerts_summary(self, alerts: Optional[List[Alert]] = None) -> Dict:
        """알림 요약 정보 생성
        
        Requirements: 8.3
        - 이슈 요약과 관련 게시글 링크 포함
        
        Args:
            alerts: 알림 목록 (None이면 내부 저장된 알림 사용)
            
        Returns:
            알림 요약 딕셔너리
        """
        target_alerts = alerts if alerts is not None else self._alerts
        
        if not target_alerts:
            return {
                "total_alerts": 0,
                "urgent_count": 0,
                "hot_issue_count": 0,
                "sentiment_spike_count": 0,
                "critical_count": 0,
                "alerts": [],
                "top_alert": None
            }
        
        urgent_count = sum(1 for a in target_alerts if a.is_urgent)
        hot_issue_count = sum(1 for a in target_alerts if a.alert_type == AlertType.HOT_ISSUE)
        sentiment_spike_count = sum(1 for a in target_alerts if a.alert_type == AlertType.SENTIMENT_SPIKE)
        critical_count = sum(1 for a in target_alerts if a.priority == AlertPriority.CRITICAL)
        
        # 가장 중요한 알림
        top_alert = target_alerts[0] if target_alerts else None
        
        return {
            "total_alerts": len(target_alerts),
            "urgent_count": urgent_count,
            "hot_issue_count": hot_issue_count,
            "sentiment_spike_count": sentiment_spike_count,
            "critical_count": critical_count,
            "alerts": [a.to_dict() for a in target_alerts],
            "top_alert": top_alert.to_dict() if top_alert else None
        }
