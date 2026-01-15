"""
GameAnalyzer 통합 클래스

Requirements: 2.1, 3.1, 4.1
- SentimentAnalyzer, IssueDetector, TrendAnalyzer 통합
- 전체 분석 파이프라인 조율
- 게임별 종합 분석 수행
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from crawler.models.data_models import PostContent
from crawler.models.analysis_models import (
    GameAnalysisResult,
    DetectedIssue,
    TrendData,
    SentimentResult
)
from crawler.models.game_profile import GameProfile, GameProfileManager
from crawler.analysis.sentiment import SentimentAnalyzer
from crawler.analysis.issue_detector import IssueDetector
from crawler.analysis.trend_analyzer import TrendAnalyzer
from crawler.analysis.alert_manager import AlertManager
from crawler.exporters.analysis_store import AnalysisDataStore


logger = logging.getLogger(__name__)


class GameAnalyzer:
    """게임 분석 통합 클래스
    
    Requirements: 2.1, 3.1, 4.1
    - 감성 분석, 이슈 탐지, 트렌드 분석을 통합
    - 전체 분석 파이프라인 조율
    - 게임별 종합 분석 결과 생성
    """
    
    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        issue_detector: Optional[IssueDetector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        alert_manager: Optional[AlertManager] = None,
        analysis_store: Optional[AnalysisDataStore] = None,
        profile_manager: Optional[GameProfileManager] = None
    ):
        """GameAnalyzer 초기화
        
        Args:
            sentiment_analyzer: 감성 분석기 (None이면 새로 생성)
            issue_detector: 이슈 탐지기 (None이면 새로 생성)
            trend_analyzer: 트렌드 분석기 (None이면 새로 생성)
            alert_manager: 알림 관리자 (None이면 새로 생성)
            analysis_store: 분석 결과 저장소 (None이면 새로 생성)
            profile_manager: 게임 프로필 관리자 (None이면 새로 생성)
        """
        # 감성 분석기 초기화
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        
        # 이슈 탐지기 초기화 (감성 분석기 공유)
        self.issue_detector = issue_detector or IssueDetector(
            sentiment_analyzer=self.sentiment_analyzer
        )
        
        # 트렌드 분석기 초기화 (감성 분석기 공유)
        self.trend_analyzer = trend_analyzer or TrendAnalyzer(
            sentiment_analyzer=self.sentiment_analyzer
        )
        
        # 알림 관리자 초기화
        self.alert_manager = alert_manager or AlertManager(
            sentiment_analyzer=self.sentiment_analyzer,
            issue_detector=self.issue_detector,
            trend_analyzer=self.trend_analyzer
        )
        
        # 분석 결과 저장소
        self.analysis_store = analysis_store or AnalysisDataStore()
        
        # 게임 프로필 관리자
        self.profile_manager = profile_manager or GameProfileManager()
        
        logger.info("GameAnalyzer 초기화 완료")
    
    def analyze(
        self,
        game_id: str,
        posts: List[PostContent],
        save_result: bool = True,
        trend_period: str = "daily"
    ) -> GameAnalysisResult:
        """게임 데이터 종합 분석
        
        Requirements: 2.1, 3.1, 4.1
        - 감성 분석, 이슈 탐지, 트렌드 분석 수행
        - 종합 분석 결과 생성
        
        Args:
            game_id: 게임 ID
            posts: 분석할 게시글 목록
            save_result: 결과 저장 여부
            trend_period: 트렌드 분석 기간 ("daily" 또는 "weekly")
            
        Returns:
            GameAnalysisResult: 종합 분석 결과
        """
        logger.info(f"게임 '{game_id}' 분석 시작: {len(posts)}개 게시글")
        
        analyzed_at = datetime.now()
        
        # 1. 감성 분석
        logger.debug("감성 분석 수행 중...")
        sentiment_distribution = self._analyze_sentiment(posts)
        sentiment_avg = self.sentiment_analyzer.get_average_sentiment(posts)
        
        # 2. 이슈 탐지
        logger.debug("이슈 탐지 수행 중...")
        issues = self.issue_detector.detect_issues(posts)
        
        # 3. Hot Issue 탐지
        hot_issues = self.issue_detector.detect_hot_issues(issues)
        
        # 4. 버그 이슈 필터링
        bug_issues = self.issue_detector.get_bug_issues(issues)
        
        # 5. 트렌드 분석
        logger.debug("트렌드 분석 수행 중...")
        sentiment_trend = self.trend_analyzer.analyze_sentiment_trend(
            posts, period=trend_period
        )
        
        # 6. 총 댓글 수 계산
        total_comments = sum(len(post.comments) for post in posts)
        
        # 7. 결과 생성
        result = GameAnalysisResult(
            game_id=game_id,
            analyzed_at=analyzed_at,
            total_posts=len(posts),
            total_comments=total_comments,
            sentiment_distribution=sentiment_distribution,
            sentiment_avg=sentiment_avg,
            issues=issues,
            hot_issues=hot_issues,
            bug_issues=bug_issues,
            sentiment_trend=sentiment_trend
        )
        
        # 8. 결과 저장
        if save_result:
            filepath = self.analysis_store.save_analysis(game_id, result)
            logger.info(f"분석 결과 저장 완료: {filepath}")
        
        logger.info(
            f"게임 '{game_id}' 분석 완료: "
            f"게시글 {len(posts)}개, 이슈 {len(issues)}개, "
            f"Hot Issue {len(hot_issues)}개, 버그 {len(bug_issues)}개"
        )
        
        return result
    
    def _analyze_sentiment(self, posts: List[PostContent]) -> Dict[str, int]:
        """게시글 목록의 감성 분포 분석
        
        Args:
            posts: 게시글 목록
            
        Returns:
            감성 분포 딕셔너리
        """
        return self.sentiment_analyzer.get_sentiment_distribution(posts)
    
    def analyze_with_alerts(
        self,
        game_id: str,
        posts: List[PostContent],
        save_result: bool = True,
        trend_period: str = "daily"
    ) -> Dict[str, Any]:
        """게임 데이터 분석 및 알림 생성
        
        Requirements: 2.1, 3.1, 4.1, 8.1, 8.2
        - 종합 분석 수행
        - 알림 생성
        
        Args:
            game_id: 게임 ID
            posts: 분석할 게시글 목록
            save_result: 결과 저장 여부
            trend_period: 트렌드 분석 기간
            
        Returns:
            분석 결과 및 알림 정보
        """
        # 분석 수행
        analysis_result = self.analyze(
            game_id=game_id,
            posts=posts,
            save_result=save_result,
            trend_period=trend_period
        )
        
        # 알림 생성
        alerts = self.alert_manager.generate_alerts(
            game_id=game_id,
            posts=posts,
            issues=analysis_result.issues
        )
        
        return {
            "analysis": analysis_result,
            "alerts": alerts,
            "alert_count": len(alerts),
            "urgent_alert_count": sum(1 for a in alerts if a.is_urgent)
        }
    
    def get_analysis_summary(self, game_id: str) -> Optional[Dict[str, Any]]:
        """게임별 분석 요약 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            분석 요약 정보 또는 None
        """
        return self.analysis_store.get_analysis_summary(game_id)
    
    def get_latest_analysis(self, game_id: str) -> Optional[GameAnalysisResult]:
        """게임별 최신 분석 결과 조회
        
        Args:
            game_id: 게임 ID
            
        Returns:
            최신 분석 결과 또는 None
        """
        return self.analysis_store.get_latest_analysis(game_id)
    
    def analyze_sentiment_only(
        self,
        posts: List[PostContent]
    ) -> Dict[str, Any]:
        """감성 분석만 수행
        
        Requirements: 2.1
        
        Args:
            posts: 분석할 게시글 목록
            
        Returns:
            감성 분석 결과
        """
        distribution = self.sentiment_analyzer.get_sentiment_distribution(posts)
        avg_score = self.sentiment_analyzer.get_average_sentiment(posts)
        negative_posts = self.sentiment_analyzer.filter_negative_posts(posts)
        
        return {
            "distribution": distribution,
            "average_score": avg_score,
            "negative_post_count": len(negative_posts),
            "total_posts": len(posts)
        }
    
    def detect_issues_only(
        self,
        posts: List[PostContent],
        top_n_keywords: int = 50
    ) -> Dict[str, Any]:
        """이슈 탐지만 수행
        
        Requirements: 3.1
        
        Args:
            posts: 분석할 게시글 목록
            top_n_keywords: 추출할 상위 키워드 수
            
        Returns:
            이슈 탐지 결과
        """
        issues = self.issue_detector.detect_issues(posts, top_n_keywords)
        hot_issues = self.issue_detector.detect_hot_issues(issues)
        bug_issues = self.issue_detector.get_bug_issues(issues)
        
        return {
            "issues": issues,
            "hot_issues": hot_issues,
            "bug_issues": bug_issues,
            "total_issues": len(issues),
            "hot_issue_count": len(hot_issues),
            "bug_issue_count": len(bug_issues)
        }
    
    def analyze_trend_only(
        self,
        posts: List[PostContent],
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TrendData:
        """트렌드 분석만 수행
        
        Requirements: 4.1
        
        Args:
            posts: 분석할 게시글 목록
            period: 분석 기간 ("daily" 또는 "weekly")
            start_date: 시작일 (선택)
            end_date: 종료일 (선택)
            
        Returns:
            트렌드 데이터
        """
        return self.trend_analyzer.analyze_sentiment_trend(
            posts=posts,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_hot_posts(
        self,
        posts: List[PostContent],
        top_n: int = 20
    ) -> Dict[str, Any]:
        """Hot Post 탐지
        
        Args:
            posts: 게시글 목록
            top_n: 반환할 Hot Post 수
            
        Returns:
            Hot Post 요약 정보
        """
        return self.issue_detector.get_hot_posts_summary(posts, top_n)
    
    def compare_periods(
        self,
        posts: List[PostContent],
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> Dict[str, Any]:
        """기간별 비교 분석
        
        Args:
            posts: 게시글 목록
            period1_start: 기간1 시작일
            period1_end: 기간1 종료일
            period2_start: 기간2 시작일
            period2_end: 기간2 종료일
            
        Returns:
            기간별 비교 결과
        """
        return self.trend_analyzer.compare_periods(
            posts=posts,
            period1_start=period1_start,
            period1_end=period1_end,
            period2_start=period2_start,
            period2_end=period2_end
        )
