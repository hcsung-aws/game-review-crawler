"""
이슈 탐지 모듈

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
- 커뮤니티에서 반복되는 이슈 탐지
- 키워드 클러스터링
- 이슈 우선순위화
- Hot Issue 탐지
"""

import uuid
import re
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from crawler.models.data_models import PostContent
from crawler.models.analysis_models import (
    KeywordCluster, 
    DetectedIssue, 
    IssueSeverity,
    SentimentResult,
    HotPost
)
from crawler.analysis.keyword_extractor import KeywordExtractor
from crawler.analysis.sentiment import SentimentAnalyzer


class IssueDetector:
    """이슈 탐지기
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    - 게시글에서 반복되는 이슈 탐지
    - 키워드 클러스터링으로 유사 이슈 그룹화
    - 우선순위 점수 계산
    - Hot Issue 탐지
    """
    
    # 버그/오류 관련 키워드
    BUG_KEYWORDS = {
        "버그", "오류", "에러", "렉", "튕김", "접속불가",
        "크래시", "프리징", "멈춤", "안됨", "불가", "안돼",
        "오작동", "작동안함", "실행안됨", "로딩", "무한로딩",
        "끊김", "팅김", "다운", "서버다운", "점검", "긴급점검",
        "bug", "error", "crash", "freeze", "lag"
    }
    
    def __init__(
        self, 
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        keyword_extractor: Optional[KeywordExtractor] = None
    ):
        """이슈 탐지기 초기화
        
        Args:
            sentiment_analyzer: 감성 분석기 (None이면 새로 생성)
            keyword_extractor: 키워드 추출기 (None이면 새로 생성)
        """
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.keyword_extractor = keyword_extractor or KeywordExtractor()
    
    def extract_keywords(self, posts: List[PostContent], top_n: int = 50) -> List[str]:
        """게시글에서 주요 키워드 추출
        
        Requirements: 3.1
        - 게시글 데이터를 분석하여 반복적으로 언급되는 키워드 추출
        
        Args:
            posts: 게시글 목록
            top_n: 반환할 상위 키워드 수
            
        Returns:
            키워드 리스트 (빈도순)
        """
        return self.keyword_extractor.extract_from_posts(posts, top_n)
    
    def _calculate_keyword_similarity(self, kw1: str, kw2: str) -> float:
        """두 키워드 간 유사도 계산 (간단한 문자열 유사도)
        
        Args:
            kw1: 첫 번째 키워드
            kw2: 두 번째 키워드
            
        Returns:
            유사도 (0.0 ~ 1.0)
        """
        # 동일한 경우
        if kw1 == kw2:
            return 1.0
        
        # 포함 관계
        if kw1 in kw2 or kw2 in kw1:
            return 0.8
        
        # 공통 문자 비율 (Jaccard 유사도)
        set1 = set(kw1)
        set2 = set(kw2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def cluster_keywords(
        self, 
        keywords: List[str], 
        similarity_threshold: float = 0.5
    ) -> List[KeywordCluster]:
        """유사 키워드 클러스터링
        
        Requirements: 3.2
        - 유사한 의미를 가진 키워드들을 그룹화
        - 모든 입력 키워드는 정확히 하나의 클러스터에 속함
        
        Args:
            keywords: 키워드 목록
            similarity_threshold: 클러스터링 유사도 임계값
            
        Returns:
            KeywordCluster 목록
        """
        if not keywords:
            return []
        
        # 각 키워드가 어느 클러스터에 속하는지 추적
        keyword_to_cluster: Dict[str, int] = {}
        clusters: List[List[str]] = []
        
        for keyword in keywords:
            # 기존 클러스터와 유사도 확인
            best_cluster_idx = -1
            best_similarity = 0.0
            
            for cluster_idx, cluster_keywords in enumerate(clusters):
                # 클러스터의 대표 키워드(첫 번째)와 유사도 계산
                representative = cluster_keywords[0]
                similarity = self._calculate_keyword_similarity(keyword, representative)
                
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster_idx = cluster_idx
            
            if best_cluster_idx >= 0:
                # 기존 클러스터에 추가
                clusters[best_cluster_idx].append(keyword)
                keyword_to_cluster[keyword] = best_cluster_idx
            else:
                # 새 클러스터 생성
                new_cluster_idx = len(clusters)
                clusters.append([keyword])
                keyword_to_cluster[keyword] = new_cluster_idx
        
        # KeywordCluster 객체 생성
        result = []
        for idx, cluster_keywords in enumerate(clusters):
            cluster = KeywordCluster(
                cluster_id=f"cluster_{idx}",
                keywords=cluster_keywords,
                representative=cluster_keywords[0],  # 첫 번째 키워드가 대표
                post_count=0,
                total_views=0,
                total_comments=0
            )
            result.append(cluster)
        
        return result
    
    def _update_cluster_stats(
        self, 
        cluster: KeywordCluster, 
        posts: List[PostContent]
    ) -> KeywordCluster:
        """클러스터 통계 업데이트
        
        Args:
            cluster: 키워드 클러스터
            posts: 게시글 목록
            
        Returns:
            통계가 업데이트된 클러스터
        """
        post_count = 0
        total_views = 0
        total_comments = 0
        
        cluster_keywords_set = set(cluster.keywords)
        
        for post in posts:
            # 게시글에서 키워드 추출
            post_keywords = set(self.keyword_extractor.extract_from_post(post, top_n=100))
            
            # 클러스터 키워드와 교집합이 있으면 관련 게시글
            if cluster_keywords_set & post_keywords:
                post_count += 1
                total_views += post.view_count
                total_comments += len(post.comments)
        
        return KeywordCluster(
            cluster_id=cluster.cluster_id,
            keywords=cluster.keywords,
            representative=cluster.representative,
            post_count=post_count,
            total_views=total_views,
            total_comments=total_comments
        )
    
    def calculate_priority(
        self, 
        cluster: KeywordCluster, 
        posts: List[PostContent],
        view_weight: float = 0.3,
        comment_weight: float = 0.3,
        frequency_weight: float = 0.4
    ) -> float:
        """이슈 우선순위 점수 계산
        
        Requirements: 3.3
        - 조회수, 댓글수, 언급 빈도를 가중 합산
        
        Args:
            cluster: 키워드 클러스터
            posts: 게시글 목록
            view_weight: 조회수 가중치
            comment_weight: 댓글수 가중치
            frequency_weight: 언급 빈도 가중치
            
        Returns:
            우선순위 점수 (0.0 이상)
        """
        if not posts:
            return 0.0
        
        # 전체 통계 계산
        total_posts = len(posts)
        total_views = sum(p.view_count for p in posts)
        total_comments = sum(len(p.comments) for p in posts)
        
        # 정규화를 위한 최대값 (0으로 나누기 방지)
        max_views = max(total_views, 1)
        max_comments = max(total_comments, 1)
        max_posts = max(total_posts, 1)
        
        # 정규화된 점수 계산
        view_score = cluster.total_views / max_views
        comment_score = cluster.total_comments / max_comments
        frequency_score = cluster.post_count / max_posts
        
        # 가중 합산
        priority = (
            view_weight * view_score +
            comment_weight * comment_score +
            frequency_weight * frequency_score
        )
        
        return priority
    
    def _is_bug_related(self, post: PostContent) -> bool:
        """버그/오류 관련 게시글 여부 확인
        
        Args:
            post: 게시글 객체
            
        Returns:
            버그 관련 여부
        """
        text = f"{post.title} {post.body}".lower()
        
        for keyword in self.BUG_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        return False
    
    def classify_bug(self, post: PostContent) -> bool:
        """버그/오류 관련 게시글 분류
        
        Requirements: 7.1, 7.2
        - "버그", "오류", "에러", "렉", "튕김", "접속불가" 등의 키워드를 기준으로 분류
        
        Args:
            post: 게시글 객체
            
        Returns:
            버그 관련 여부
        """
        return self._is_bug_related(post)
    
    def classify_bug_from_text(self, text: str) -> bool:
        """텍스트에서 버그/오류 관련 여부 분류
        
        Requirements: 7.1, 7.2
        - "버그", "오류", "에러", "렉", "튕김", "접속불가" 등의 키워드를 기준으로 분류
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            버그 관련 여부
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for keyword in self.BUG_KEYWORDS:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def get_bug_keywords_found(self, text: str) -> List[str]:
        """텍스트에서 발견된 버그 키워드 목록 반환
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            발견된 버그 키워드 목록
        """
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.BUG_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def calculate_severity(
        self, 
        issue: DetectedIssue,
        max_post_count: int = 100,
        frequency_weight: float = 0.5,
        sentiment_weight: float = 0.5
    ) -> IssueSeverity:
        """버그 심각도 계산
        
        Requirements: 7.4
        - 언급 빈도와 부정적 감성 강도를 기반으로 심각도 계산
        - 언급 빈도가 높고 부정적 감성이 강할수록 심각도가 높음
        
        Args:
            issue: 탐지된 이슈
            max_post_count: 정규화를 위한 최대 게시글 수 (기본값: 100)
            frequency_weight: 언급 빈도 가중치 (기본값: 0.5)
            sentiment_weight: 감성 강도 가중치 (기본값: 0.5)
            
        Returns:
            심각도 레벨
        """
        # 언급 빈도 정규화 (0 ~ 1)
        frequency_factor = min(1.0, issue.cluster.post_count / max(max_post_count, 1))
        
        # 부정적 감성 강도 (0 ~ 1)
        # sentiment_avg는 -1.0 ~ 1.0 범위, 부정적일수록 높은 값으로 변환
        sentiment_factor = max(0.0, -issue.sentiment_avg)  # 0 ~ 1
        
        # 종합 점수 계산
        severity_score = (
            frequency_weight * frequency_factor +
            sentiment_weight * sentiment_factor
        )
        
        # 심각도 결정
        if severity_score >= 0.7:
            return IssueSeverity.CRITICAL
        elif severity_score >= 0.5:
            return IssueSeverity.HIGH
        elif severity_score >= 0.3:
            return IssueSeverity.MEDIUM
        else:
            return IssueSeverity.LOW
    
    def calculate_severity_from_metrics(
        self,
        post_count: int,
        sentiment_avg: float,
        max_post_count: int = 100,
        frequency_weight: float = 0.5,
        sentiment_weight: float = 0.5
    ) -> IssueSeverity:
        """메트릭 값으로부터 직접 심각도 계산
        
        Requirements: 7.4
        - 언급 빈도와 부정적 감성 강도를 기반으로 심각도 계산
        
        Args:
            post_count: 언급 빈도 (게시글 수)
            sentiment_avg: 평균 감성 점수 (-1.0 ~ 1.0)
            max_post_count: 정규화를 위한 최대 게시글 수
            frequency_weight: 언급 빈도 가중치
            sentiment_weight: 감성 강도 가중치
            
        Returns:
            심각도 레벨
        """
        # 언급 빈도 정규화 (0 ~ 1)
        frequency_factor = min(1.0, post_count / max(max_post_count, 1))
        
        # 부정적 감성 강도 (0 ~ 1)
        sentiment_factor = max(0.0, -sentiment_avg)
        
        # 종합 점수 계산
        severity_score = (
            frequency_weight * frequency_factor +
            sentiment_weight * sentiment_factor
        )
        
        # 심각도 결정
        if severity_score >= 0.7:
            return IssueSeverity.CRITICAL
        elif severity_score >= 0.5:
            return IssueSeverity.HIGH
        elif severity_score >= 0.3:
            return IssueSeverity.MEDIUM
        else:
            return IssueSeverity.LOW
    
    def detect_issues(
        self, 
        posts: List[PostContent],
        top_n_keywords: int = 50,
        similarity_threshold: float = 0.5
    ) -> List[DetectedIssue]:
        """이슈 탐지 및 우선순위화
        
        Requirements: 3.1, 3.2, 3.3, 3.5
        - 게시글에서 이슈 탐지
        - 우선순위 순으로 정렬하여 반환
        
        Args:
            posts: 게시글 목록
            top_n_keywords: 추출할 상위 키워드 수
            similarity_threshold: 클러스터링 유사도 임계값
            
        Returns:
            DetectedIssue 목록 (우선순위 내림차순)
        """
        if not posts:
            return []
        
        # 1. 키워드 추출
        keywords = self.extract_keywords(posts, top_n_keywords)
        
        if not keywords:
            return []
        
        # 2. 키워드 클러스터링
        clusters = self.cluster_keywords(keywords, similarity_threshold)
        
        # 3. 클러스터 통계 업데이트 및 이슈 생성
        issues = []
        keyword_post_mapping = self.keyword_extractor.get_keyword_post_mapping(posts, top_n_keywords)
        
        for cluster in clusters:
            # 클러스터 통계 업데이트
            updated_cluster = self._update_cluster_stats(cluster, posts)
            
            # 관련 게시글 URL 수집
            related_posts = set()
            for keyword in updated_cluster.keywords:
                if keyword in keyword_post_mapping:
                    related_posts.update(keyword_post_mapping[keyword])
            
            # 관련 게시글의 감성 평균 계산
            related_post_objects = [p for p in posts if p.url in related_posts]
            sentiment_avg = 0.0
            if related_post_objects:
                sentiment_avg = self.sentiment_analyzer.get_average_sentiment(related_post_objects)
            
            # 버그 관련 여부 확인
            is_bug = any(
                kw.lower() in self.BUG_KEYWORDS or 
                any(bug_kw in kw.lower() for bug_kw in self.BUG_KEYWORDS)
                for kw in updated_cluster.keywords
            )
            
            # 최초 발견 시간 (가장 오래된 관련 게시글)
            first_seen = None
            if related_post_objects:
                posts_with_date = [p for p in related_post_objects if p.created_at]
                if posts_with_date:
                    first_seen = min(p.created_at for p in posts_with_date)
            
            # 우선순위 계산
            priority_score = self.calculate_priority(updated_cluster, posts)
            
            # 이슈 생성
            issue = DetectedIssue(
                issue_id=f"issue_{uuid.uuid4().hex[:8]}",
                title=updated_cluster.representative,
                cluster=updated_cluster,
                priority_score=priority_score,
                is_hot=False,  # 나중에 detect_hot_issues에서 설정
                is_bug=is_bug,
                severity=IssueSeverity.LOW,  # 나중에 설정
                related_posts=list(related_posts),
                first_seen=first_seen,
                sentiment_avg=sentiment_avg
            )
            
            # 버그인 경우 심각도 계산
            if is_bug:
                issue.severity = self.calculate_severity(issue, max_post_count=len(posts))
            
            issues.append(issue)
        
        # 4. 우선순위 내림차순 정렬
        issues.sort(key=lambda x: x.priority_score, reverse=True)
        
        return issues
    
    def detect_hot_issues(
        self, 
        issues: List[DetectedIssue], 
        threshold_percentile: float = 0.9
    ) -> List[DetectedIssue]:
        """Hot Issue 탐지
        
        Requirements: 3.4
        - Issue_Priority 상위 10%를 Hot_Issue로 분류
        
        Args:
            issues: 이슈 목록
            threshold_percentile: Hot Issue 임계 백분위 (기본값: 0.9 = 상위 10%)
            
        Returns:
            Hot Issue 목록 (is_hot=True로 설정됨)
        """
        if not issues:
            return []
        
        # 우선순위 점수로 정렬
        sorted_issues = sorted(issues, key=lambda x: x.priority_score, reverse=True)
        
        # 상위 N% 계산
        hot_count = max(1, int(len(sorted_issues) * (1 - threshold_percentile)))
        
        # Hot Issue 설정
        hot_issues = []
        for i, issue in enumerate(sorted_issues):
            if i < hot_count:
                issue.is_hot = True
                hot_issues.append(issue)
        
        return hot_issues
    
    def get_bug_issues(self, issues: List[DetectedIssue]) -> List[DetectedIssue]:
        """버그 관련 이슈 필터링
        
        Requirements: 7.3
        - 버그 관련 이슈만 필터링하여 반환
        
        Args:
            issues: 이슈 목록
            
        Returns:
            버그 관련 이슈 목록 (심각도 순 정렬)
        """
        bug_issues = [issue for issue in issues if issue.is_bug]
        
        # 심각도 순으로 정렬 (CRITICAL > HIGH > MEDIUM > LOW)
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3
        }
        
        bug_issues.sort(key=lambda x: (severity_order.get(x.severity, 4), -x.priority_score))
        
        return bug_issues
    
    def detect_bug_issues(
        self, 
        posts: List[PostContent],
        top_n_keywords: int = 50,
        similarity_threshold: float = 0.5
    ) -> List[DetectedIssue]:
        """버그 관련 이슈만 탐지
        
        Requirements: 7.1, 7.2, 7.3, 7.4
        - 버그/오류 관련 게시글에서 이슈 탐지
        - 심각도 계산 및 정렬
        
        Args:
            posts: 게시글 목록
            top_n_keywords: 추출할 상위 키워드 수
            similarity_threshold: 클러스터링 유사도 임계값
            
        Returns:
            버그 관련 DetectedIssue 목록 (심각도 순)
        """
        # 전체 이슈 탐지
        all_issues = self.detect_issues(posts, top_n_keywords, similarity_threshold)
        
        # 버그 이슈만 필터링
        return self.get_bug_issues(all_issues)
    
    def get_bug_posts(self, posts: List[PostContent]) -> List[PostContent]:
        """버그 관련 게시글만 필터링
        
        Requirements: 7.1, 7.2
        - 버그/오류 관련 키워드가 포함된 게시글만 반환
        
        Args:
            posts: 게시글 목록
            
        Returns:
            버그 관련 게시글 목록
        """
        return [post for post in posts if self.classify_bug(post)]
    
    def detect_urgent_issues(
        self, 
        posts: List[PostContent],
        hours: int = 24,
        min_posts: int = 10
    ) -> List[DetectedIssue]:
        """긴급 이슈 탐지
        
        Requirements: 8.4
        - 24시간 내 동일 이슈에 대한 게시글이 10개 이상이면 긴급 이슈
        
        Args:
            posts: 게시글 목록
            hours: 시간 범위 (기본값: 24시간)
            min_posts: 최소 게시글 수 (기본값: 10개)
            
        Returns:
            긴급 이슈 목록
        """
        if not posts:
            return []
        
        # 최근 N시간 내 게시글 필터링
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        
        recent_posts = [
            p for p in posts 
            if p.created_at and p.created_at >= cutoff_time
        ]
        
        if len(recent_posts) < min_posts:
            return []
        
        # 이슈 탐지
        issues = self.detect_issues(recent_posts)
        
        # 게시글 수가 min_posts 이상인 이슈만 긴급 이슈로 분류
        urgent_issues = [
            issue for issue in issues 
            if issue.cluster.post_count >= min_posts
        ]
        
        return urgent_issues

    def calculate_post_hot_score(
        self,
        post: PostContent,
        max_views: int,
        max_comments: int,
        view_weight: float = 0.4,
        comment_weight: float = 0.3,
        sentiment_weight: float = 0.3
    ) -> float:
        """게시글의 Hot Score 계산
        
        Args:
            post: 게시글 객체
            max_views: 정규화를 위한 최대 조회수
            max_comments: 정규화를 위한 최대 댓글수
            view_weight: 조회수 가중치
            comment_weight: 댓글수 가중치
            sentiment_weight: 감성 가중치 (부정적일수록 높은 점수)
            
        Returns:
            Hot Score (0.0 ~ 1.0)
        """
        # 조회수 정규화
        view_score = post.view_count / max(max_views, 1)
        
        # 댓글수 정규화
        comment_count = len(post.comments)
        comment_score = comment_count / max(max_comments, 1)
        
        # 감성 점수 (부정적일수록 높은 점수 - 문제 게시글 우선)
        sentiment_result = self.sentiment_analyzer.analyze_post(post)
        # -1.0 ~ 1.0을 0.0 ~ 1.0으로 변환 (부정적일수록 높음)
        sentiment_score = (1.0 - sentiment_result.score) / 2.0
        
        # 가중 합산
        hot_score = (
            view_weight * min(view_score, 1.0) +
            comment_weight * min(comment_score, 1.0) +
            sentiment_weight * sentiment_score
        )
        
        return min(hot_score, 1.0)

    def detect_hot_posts(
        self,
        posts: List[PostContent],
        top_n: int = 20,
        threshold_percentile: float = 0.9,
        view_weight: float = 0.4,
        comment_weight: float = 0.3,
        sentiment_weight: float = 0.3
    ) -> List[HotPost]:
        """게시글 기반 Hot Post 탐지
        
        각 게시글에 점수를 부여하고 상위 N개 또는 상위 10%를 Hot Post로 반환
        
        Args:
            posts: 게시글 목록
            top_n: 반환할 최대 Hot Post 수
            threshold_percentile: Hot Post 임계 백분위 (기본값: 0.9 = 상위 10%)
            view_weight: 조회수 가중치
            comment_weight: 댓글수 가중치
            sentiment_weight: 감성 가중치
            
        Returns:
            HotPost 목록 (hot_score 내림차순)
        """
        if not posts:
            return []
        
        # 정규화를 위한 최대값 계산
        max_views = max((p.view_count for p in posts), default=1)
        max_comments = max((len(p.comments) for p in posts), default=1)
        
        # 각 게시글의 Hot Score 계산
        scored_posts = []
        for post in posts:
            hot_score = self.calculate_post_hot_score(
                post, max_views, max_comments,
                view_weight, comment_weight, sentiment_weight
            )
            
            # 감성 분석
            sentiment_result = self.sentiment_analyzer.analyze_post(post)
            
            # 버그 관련 여부
            is_bug = self._is_bug_related(post)
            
            # 키워드 추출
            keywords = self.keyword_extractor.extract_from_post(post, top_n=5)
            
            # 심각도 계산 (버그인 경우)
            severity = IssueSeverity.LOW
            if is_bug:
                # 부정적 감성 + 높은 hot_score = 높은 심각도
                severity_score = (hot_score * 0.6) + (max(0, -sentiment_result.score) * 0.4)
                if severity_score >= 0.7:
                    severity = IssueSeverity.CRITICAL
                elif severity_score >= 0.5:
                    severity = IssueSeverity.HIGH
                elif severity_score >= 0.3:
                    severity = IssueSeverity.MEDIUM
            
            hot_post = HotPost(
                post_url=post.url,
                title=post.title,
                author=post.author or "",
                site=post.site,
                created_at=post.created_at,
                view_count=post.view_count,
                comment_count=len(post.comments),
                like_count=post.like_count,
                hot_score=hot_score,
                sentiment_score=sentiment_result.score,
                is_bug=is_bug,
                severity=severity,
                keywords=keywords
            )
            scored_posts.append(hot_post)
        
        # Hot Score 내림차순 정렬
        scored_posts.sort(key=lambda x: x.hot_score, reverse=True)
        
        # 상위 N% 또는 top_n 중 작은 값
        hot_count = max(1, int(len(scored_posts) * (1 - threshold_percentile)))
        hot_count = min(hot_count, top_n, len(scored_posts))
        
        return scored_posts[:hot_count]

    def get_hot_posts_summary(
        self,
        posts: List[PostContent],
        top_n: int = 10
    ) -> Dict:
        """Hot Post 요약 정보 반환
        
        Args:
            posts: 게시글 목록
            top_n: 반환할 Hot Post 수
            
        Returns:
            요약 정보 딕셔너리
        """
        hot_posts = self.detect_hot_posts(posts, top_n=top_n)
        
        if not hot_posts:
            return {
                "total_hot_posts": 0,
                "hot_posts": [],
                "bug_count": 0,
                "critical_count": 0,
                "alert_message": None
            }
        
        bug_count = sum(1 for p in hot_posts if p.is_bug)
        critical_count = sum(1 for p in hot_posts if p.severity == IssueSeverity.CRITICAL)
        
        # 알림 메시지 생성
        alert_message = None
        top_post = hot_posts[0]
        if top_post.hot_score >= 0.7:
            alert_message = f"🔥 긴급: '{top_post.title[:50]}...' - 조회수 {top_post.view_count:,}, 댓글 {top_post.comment_count}개"
        elif top_post.hot_score >= 0.5:
            alert_message = f"⚠️ 주목: '{top_post.title[:50]}...' - 조회수 {top_post.view_count:,}"
        
        return {
            "total_hot_posts": len(hot_posts),
            "hot_posts": [p.to_dict() for p in hot_posts],
            "bug_count": bug_count,
            "critical_count": critical_count,
            "alert_message": alert_message
        }
