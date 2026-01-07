"""
분석용 데이터 모델 정의

Requirements: 2.1, 3.2, 4.1
- SentimentResult: 감성 분석 결과
- KeywordCluster: 키워드 클러스터
- DetectedIssue: 탐지된 이슈
- TrendPoint: 트렌드 데이터 포인트
- TrendData: 트렌드 데이터
- GameAnalysisResult: 게임 분석 결과
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class SentimentLabel(Enum):
    """감성 레이블"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class IssueSeverity(Enum):
    """이슈 심각도"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SentimentResult:
    """감성 분석 결과
    
    Requirements: 2.1, 2.2
    - score: -1.0 ~ 1.0 범위의 감성 점수
    - label: 긍정/부정/중립 레이블
    - confidence: 신뢰도 (0.0 ~ 1.0)
    """
    score: float
    label: SentimentLabel
    confidence: float = 1.0
    
    def __post_init__(self):
        # score 범위 검증
        if not -1.0 <= self.score <= 1.0:
            raise ValueError(f"score must be between -1.0 and 1.0, got {self.score}")
        # confidence 범위 검증
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "score": self.score,
            "label": self.label.value,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SentimentResult":
        """딕셔너리에서 객체 생성"""
        return cls(
            score=data["score"],
            label=SentimentLabel(data["label"]),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class KeywordCluster:
    """키워드 클러스터
    
    Requirements: 3.2
    - 유사한 의미를 가진 키워드들의 그룹
    """
    cluster_id: str
    keywords: List[str]
    representative: str
    post_count: int = 0
    total_views: int = 0
    total_comments: int = 0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "cluster_id": self.cluster_id,
            "keywords": self.keywords,
            "representative": self.representative,
            "post_count": self.post_count,
            "total_views": self.total_views,
            "total_comments": self.total_comments
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KeywordCluster":
        """딕셔너리에서 객체 생성"""
        return cls(
            cluster_id=data["cluster_id"],
            keywords=data["keywords"],
            representative=data["representative"],
            post_count=data.get("post_count", 0),
            total_views=data.get("total_views", 0),
            total_comments=data.get("total_comments", 0)
        )


@dataclass
class DetectedIssue:
    """탐지된 이슈
    
    Requirements: 3.2, 3.3, 3.4, 3.5
    - 커뮤니티에서 반복적으로 언급되는 이슈
    """
    issue_id: str
    title: str
    cluster: KeywordCluster
    priority_score: float
    is_hot: bool = False
    is_bug: bool = False
    severity: IssueSeverity = IssueSeverity.LOW
    related_posts: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    sentiment_avg: float = 0.0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "issue_id": self.issue_id,
            "title": self.title,
            "cluster": self.cluster.to_dict(),
            "priority_score": self.priority_score,
            "is_hot": self.is_hot,
            "is_bug": self.is_bug,
            "severity": self.severity.value,
            "related_posts": self.related_posts,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "sentiment_avg": self.sentiment_avg
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DetectedIssue":
        """딕셔너리에서 객체 생성"""
        first_seen = None
        if data.get("first_seen"):
            first_seen = datetime.fromisoformat(data["first_seen"])
        return cls(
            issue_id=data["issue_id"],
            title=data["title"],
            cluster=KeywordCluster.from_dict(data["cluster"]),
            priority_score=data["priority_score"],
            is_hot=data.get("is_hot", False),
            is_bug=data.get("is_bug", False),
            severity=IssueSeverity(data.get("severity", "low")),
            related_posts=data.get("related_posts", []),
            first_seen=first_seen,
            sentiment_avg=data.get("sentiment_avg", 0.0)
        )


@dataclass
class TrendPoint:
    """트렌드 데이터 포인트
    
    Requirements: 4.1
    - 특정 시점의 트렌드 값
    """
    date: datetime
    value: float
    count: int = 0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "date": self.date.isoformat(),
            "value": self.value,
            "count": self.count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrendPoint":
        """딕셔너리에서 객체 생성"""
        return cls(
            date=datetime.fromisoformat(data["date"]),
            value=data["value"],
            count=data.get("count", 0)
        )


@dataclass
class TrendData:
    """트렌드 데이터
    
    Requirements: 4.1
    - 시계열 트렌드 데이터
    """
    metric_name: str
    period: str  # "daily", "weekly"
    data_points: List[TrendPoint] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "metric_name": self.metric_name,
            "period": self.period,
            "data_points": [p.to_dict() for p in self.data_points]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrendData":
        """딕셔너리에서 객체 생성"""
        return cls(
            metric_name=data["metric_name"],
            period=data["period"],
            data_points=[TrendPoint.from_dict(p) for p in data.get("data_points", [])]
        )


@dataclass
class HotPost:
    """핫 게시글
    
    게시글 기반 Hot Issue - 조회수, 댓글수, 감성 점수를 기반으로 점수화
    """
    post_url: str
    title: str
    author: str
    site: str
    created_at: Optional[datetime]
    view_count: int
    comment_count: int
    like_count: int
    hot_score: float  # 종합 점수 (0.0 ~ 1.0)
    sentiment_score: float  # 감성 점수 (-1.0 ~ 1.0)
    is_bug: bool = False
    severity: IssueSeverity = IssueSeverity.LOW
    keywords: List[str] = field(default_factory=list)  # 게시글의 주요 키워드
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "post_url": self.post_url,
            "title": self.title,
            "author": self.author,
            "site": self.site,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "view_count": self.view_count,
            "comment_count": self.comment_count,
            "like_count": self.like_count,
            "hot_score": self.hot_score,
            "sentiment_score": self.sentiment_score,
            "is_bug": self.is_bug,
            "severity": self.severity.value,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "HotPost":
        """딕셔너리에서 객체 생성"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        return cls(
            post_url=data["post_url"],
            title=data["title"],
            author=data.get("author", ""),
            site=data.get("site", ""),
            created_at=created_at,
            view_count=data.get("view_count", 0),
            comment_count=data.get("comment_count", 0),
            like_count=data.get("like_count", 0),
            hot_score=data["hot_score"],
            sentiment_score=data.get("sentiment_score", 0.0),
            is_bug=data.get("is_bug", False),
            severity=IssueSeverity(data.get("severity", "low")),
            keywords=data.get("keywords", [])
        )


@dataclass
class GameAnalysisResult:
    """게임 분석 결과
    
    Requirements: 2.1, 3.2, 4.1
    - 게임별 종합 분석 결과
    """
    game_id: str
    analyzed_at: datetime
    total_posts: int
    total_comments: int
    sentiment_distribution: Dict[str, int]  # {"positive": n, "negative": n, "neutral": n}
    sentiment_avg: float
    issues: List[DetectedIssue]
    hot_issues: List[DetectedIssue]
    bug_issues: List[DetectedIssue]
    sentiment_trend: Optional[TrendData] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "game_id": self.game_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "total_posts": self.total_posts,
            "total_comments": self.total_comments,
            "sentiment_distribution": self.sentiment_distribution,
            "sentiment_avg": self.sentiment_avg,
            "issues": [i.to_dict() for i in self.issues],
            "hot_issues": [i.to_dict() for i in self.hot_issues],
            "bug_issues": [i.to_dict() for i in self.bug_issues],
            "sentiment_trend": self.sentiment_trend.to_dict() if self.sentiment_trend else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GameAnalysisResult":
        """딕셔너리에서 객체 생성"""
        return cls(
            game_id=data["game_id"],
            analyzed_at=datetime.fromisoformat(data["analyzed_at"]),
            total_posts=data["total_posts"],
            total_comments=data["total_comments"],
            sentiment_distribution=data["sentiment_distribution"],
            sentiment_avg=data["sentiment_avg"],
            issues=[DetectedIssue.from_dict(i) for i in data.get("issues", [])],
            hot_issues=[DetectedIssue.from_dict(i) for i in data.get("hot_issues", [])],
            bug_issues=[DetectedIssue.from_dict(i) for i in data.get("bug_issues", [])],
            sentiment_trend=TrendData.from_dict(data["sentiment_trend"]) if data.get("sentiment_trend") else None
        )
